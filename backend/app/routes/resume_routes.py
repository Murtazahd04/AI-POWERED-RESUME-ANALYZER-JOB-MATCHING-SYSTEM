import logging
from collections.abc import Awaitable, Callable

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pymongo import DESCENDING
from ..services.scoring_service import compute_score
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..schemas import ParsedResumeUpdate, ReparseRequest
from ..services.ai_analysis_service import (
    AIAnalysisError,
    analyze_full_resume,
    analyze_resume_education,
    analyze_resume_experience,
    analyze_resume_projects,
    analyze_resume_skills,
    analyze_resume_strengths,
    analyze_resume_weaknesses,
    generate_resume_summary,
    generate_improvement_suggestions,
    clear_provider_usage,
    get_provider_usage,
)
from ..services.ai_cost_service import calculate_estimated_costs
from ..services.ai_parser_service import parse_resume_with_ai
from ..services.parser_service import ParseError, extract_text, parse_resume
from ..services.storage_service import delete_resume, upload_resume
from ..utils import now, serialize, to_object_id
from ..services.scoring_service import compute_score
router = APIRouter(prefix="/api/resumes", tags=["resumes"])
log = logging.getLogger("resumes")

HIDDEN_FIELDS = ("cloudinary_public_id", "user_id")


def _detect_type(filename: str, data: bytes) -> str:
    """Check the extension AND the file's first bytes, so a renamed .txt can't sneak in."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("pdf", "docx"):
        raise HTTPException(status_code=415, detail="Only PDF and DOCX files are supported.")
    if ext == "pdf" and not data.startswith(b"%PDF"):
        raise HTTPException(status_code=422, detail="This file is not a valid PDF. It may be corrupted.")
    if ext == "docx" and not data.startswith(b"PK"):
        raise HTTPException(status_code=422, detail="This file is not a valid DOCX. It may be corrupted.")
    return ext


async def _get_owned(resume_id: str, user: dict) -> dict:
    doc = await get_db().resumes.find_one({"_id": to_object_id(resume_id), "user_id": user["_id"]})
    if doc is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return doc


async def _save_ai_result(resume_id: str, user: dict, analysis_type: str, result: dict) -> dict:
    generated_at = now()
    update_result = await get_db().resumes.update_one(
        {"_id": to_object_id(resume_id), "user_id": user["_id"]},
        {
            "$set": {
                f"ai_results.{analysis_type}": {
                    "result": result,
                    "generated_at": generated_at,
                },
            },
        },
    )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return {
        "id": resume_id,
        "analysis": {
            "type": analysis_type,
            "result": result,
            "generated_at": generated_at,
        },
    }


async def _record_ai_usage(
    user: dict,
    resume_id: str,
    operation: str,
    model: str,
    status: str,
    error_status_code: int | None = None,
    result: dict | None = None,
) -> None:
    usage = get_provider_usage()
    settings = get_settings()
    pricing_version_ref = getattr(settings, "ai_pricing_version", "unconfigured")
    try:
        model_rates = getattr(settings, "ai_model_rates", {})
    except ValueError as exc:
        # Usage accounting must never turn a completed AI analysis into a 500.
        log.warning("AI cost rates are invalid; recording usage without a cost estimate: %s", exc)
        model_rates = {}
    costs = calculate_estimated_costs(
        usage.get("input_tokens") if usage else None,
        usage.get("output_tokens") if usage else None,
        model_rates.get(model),
        pricing_version_ref,
    )
    event = {
        "user_id": user["_id"],
        "resume_id": to_object_id(resume_id),
        "model": model,
        "operation": operation,
        "timestamp": now(),
        "status": status,
        "provider_reported_usage": usage is not None,
        "input_tokens": usage.get("input_tokens") if usage else None,
        "output_tokens": usage.get("output_tokens") if usage else None,
        "pricing_version_ref": pricing_version_ref,
        **costs,
    }
    if operation in {"improvement_suggestions", "full_resume"} and result is not None:
        suggestions = (
            result.get("suggestions", [])
            if operation == "improvement_suggestions"
            else result.get("improvement_suggestions", [])
        )
        recommendation_count = len(suggestions)
        event["recommendation_count"] = recommendation_count
        event["recommendation_cost_attribution"] = (
            "allocated_from_dedicated_recommendation_request_total"
            if operation == "improvement_suggestions"
            else "allocated_from_combined_full_resume_request_total"
        )
        event["estimated_cost_per_recommendation_usd"] = (
            round(costs["estimated_total_cost_usd"] / recommendation_count, 12)
            if costs["estimated_total_cost_usd"] is not None and recommendation_count
            else None
        )
    if error_status_code is not None:
        event["error_status_code"] = error_status_code
    try:
        await get_db().ai_usage_events.insert_one(event)
    except Exception as exc:
        log.exception("Could not record AI usage event for %s: %s", operation, exc)


async def _run_ai_analysis(
    resume_id: str,
    user: dict,
    operation: str,
    model: str,
    request: Callable[[], Awaitable[dict]],
) -> dict:
    clear_provider_usage()
    try:
        result = await request()
    except AIAnalysisError as exc:
        await _record_ai_usage(user, resume_id, operation, model, "failed", exc.status_code)
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except Exception:
        await _record_ai_usage(user, resume_id, operation, model, "failed")
        raise
    await _record_ai_usage(user, resume_id, operation, model, "succeeded", result=result)
    return await _save_ai_result(resume_id, user, operation, result)


@router.post("", status_code=201)
async def upload(file: UploadFile, user: dict = Depends(get_current_user)):
    s = get_settings()
    db = get_db()

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > s.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File is too large. Maximum size is {s.max_upload_mb} MB.")
    file_type = _detect_type(file.filename or "", data)

    # NEW: read the file and extract structured data before storing anything
    try:
        raw_text = await run_in_threadpool(extract_text, data, file_type)
        parsed = await run_in_threadpool(parse_resume, raw_text)
    except ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    count = await db.resumes.count_documents({"user_id": user["_id"]})
    if count >= s.max_resumes_per_user:
        raise HTTPException(
            status_code=409,
            detail=f"You can keep at most {s.max_resumes_per_user} resumes. Delete one first.",
        )

    try:
        stored = await run_in_threadpool(upload_resume, data, file.filename, str(user["_id"]))
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        log.warning("Cloudinary upload failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Could not upload to Cloudinary: {str(exc)[:200]}") from exc

    doc = {
        "user_id": user["_id"],
        "filename": file.filename,
        "file_type": file_type,
        "size_bytes": len(data),
        "file_url": stored["url"],
        "cloudinary_public_id": stored["public_id"],
        "parsed": parsed,  # NEW
        "parser_used": "spacy",
        "parsed_at": now(),
        "uploaded_at": now(),
    }
    result = await db.resumes.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize(doc, drop=HIDDEN_FIELDS)


@router.get("")
async def list_resumes(user: dict = Depends(get_current_user)):
    cursor = get_db().resumes.find({"user_id": user["_id"]}).sort("uploaded_at", DESCENDING)
    return [serialize(d, drop=HIDDEN_FIELDS) async for d in cursor]


@router.get("/{resume_id}")
async def get_resume(resume_id: str, user: dict = Depends(get_current_user)):
    return serialize(await _get_owned(resume_id, user), drop=HIDDEN_FIELDS)


@router.put("/{resume_id}/parsed")
async def update_parsed_resume(
    resume_id: str,
    parsed: ParsedResumeUpdate,
    user: dict = Depends(get_current_user),
):
    doc = await _get_owned(resume_id, user)
    parsed_data = parsed.model_dump(mode="json")
    result = await get_db().resumes.update_one(
        {"_id": doc["_id"], "user_id": user["_id"]},
        {"$set": {"parsed": parsed_data, "ai_results": {}}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return {"id": resume_id, "parsed": parsed_data}


@router.post("/{resume_id}/skill-analysis")
async def analyze_skills(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before analyzing its skills.")

    settings = get_settings()
    return await _run_ai_analysis(
        resume_id, user, "skills", settings.ai_model_name, lambda: analyze_resume_skills(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        ),
    )


@router.post("/{resume_id}/experience-analysis")
async def analyze_experience(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before analyzing its experience.")

    settings = get_settings()
    return await _run_ai_analysis(
        resume_id, user, "experience", settings.ai_model_name, lambda: analyze_resume_experience(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        ),
    )


@router.post("/{resume_id}/education-analysis")
async def analyze_education(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before analyzing its education.")

    settings = get_settings()
    return await _run_ai_analysis(
        resume_id, user, "education", settings.ai_model_name, lambda: analyze_resume_education(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        ),
    )


@router.post("/{resume_id}/project-analysis")
async def analyze_projects(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before analyzing its projects.")

    settings = get_settings()
    return await _run_ai_analysis(
        resume_id, user, "projects", settings.ai_model_name, lambda: analyze_resume_projects(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        ),
    )


@router.post("/{resume_id}/strengths-analysis")
async def analyze_strengths(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before analyzing its strengths.")

    settings = get_settings()
    return await _run_ai_analysis(
        resume_id, user, "strengths", settings.ai_model_name, lambda: analyze_resume_strengths(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        ),
    )


@router.post("/{resume_id}/weaknesses-analysis")
async def analyze_weaknesses(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before analyzing its weaknesses.")

    settings = get_settings()
    return await _run_ai_analysis(
        resume_id, user, "weaknesses", settings.ai_model_name, lambda: analyze_resume_weaknesses(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        ),
    )


@router.post("/{resume_id}/summary-analysis")
async def analyze_resume_summary(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before generating its summary.")

    settings = get_settings()
    return await _run_ai_analysis(
        resume_id, user, "summary", settings.ai_model_name, lambda: generate_resume_summary(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        ),
    )


@router.post("/{resume_id}/full-analysis")
async def analyze_full_resume_route(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before running its analysis.")

    settings = get_settings()
    return await _run_ai_analysis(
        resume_id, user, "full_resume", settings.ai_model_name, lambda: analyze_full_resume(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        ),
    )


@router.post("/{resume_id}/improvement-suggestions")
async def suggest_resume_improvements(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(
            status_code=409,
            detail="Parse this resume before generating improvement suggestions.",
        )

    settings = get_settings()
    return await _run_ai_analysis(
        resume_id, user, "improvement_suggestions", settings.ai_model_name, lambda: generate_improvement_suggestions(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        ),
    )


# NEW: re-run parsing on a resume that was uploaded before this feature existed
@router.post("/{resume_id}/parse")
async def reparse(
    resume_id: str,
    body: ReparseRequest,
    user: dict = Depends(get_current_user),
):
    doc = await _get_owned(resume_id, user)
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(doc["file_url"])
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not re-download the file from Cloudinary.")
    try:
        raw_text = await run_in_threadpool(extract_text, resp.content, doc["file_type"])
    except ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if body.parser == "spacy":
        try:
            parsed = await run_in_threadpool(parse_resume, raw_text)
        except ParseError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            log.exception("spaCy parsing failed: %s", exc)
            raise HTTPException(status_code=422, detail=f"spaCy parsing error: {exc}") from exc
    else:
        settings = get_settings()
        try:
            parsed = await parse_resume_with_ai(
                raw_text,
                settings.ai_api_key,
                settings.ai_model_name,
                settings.max_ai_parse_chars,
            )
        except AIAnalysisError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except Exception as exc:
            log.exception("AI parsing failed: %s", exc)
            raise HTTPException(status_code=502, detail=f"AI parsing error: {exc}") from exc
    parsed_at = now()
    update_result = await get_db().resumes.update_one(
        {"_id": doc["_id"], "user_id": user["_id"]},
        {
            "$set": {
                "parsed": parsed,
                "ai_results": {},
                "parser_used": body.parser,
                "parsed_at": parsed_at,
            },
        },
    )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return {
        "id": resume_id,
        "parsed": parsed,
        "parser_used": body.parser,
        "parsed_at": parsed_at,
    }


@router.delete("/{resume_id}", status_code=204)
async def delete(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    try:
        await run_in_threadpool(delete_resume, doc["cloudinary_public_id"])
    except Exception as exc:  # even if Cloudinary cleanup fails, still remove the record
        log.warning("Cloudinary delete failed: %s", exc)
    await get_db().resumes.delete_one({"_id": doc["_id"]})

@router.get("/{resume_id}/score")
async def get_resume_score(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before scoring it.")
    try:
        score = compute_score(doc["parsed"])
    except (KeyError, TypeError, ZeroDivisionError) as exc:
        raise HTTPException(status_code=422, detail=f"Could not score this resume: {exc}") from exc
    await get_db().resumes.update_one({"_id": doc["_id"]}, {"$set": {"score": score}})
    return score