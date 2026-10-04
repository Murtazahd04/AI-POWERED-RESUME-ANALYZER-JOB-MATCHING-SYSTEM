import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pymongo import DESCENDING

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..schemas import ParsedResumeUpdate
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
)
from ..services.parser_service import ParseError, extract_text, parse_resume
from ..services.storage_service import delete_resume, upload_resume
from ..utils import now, serialize, to_object_id

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
    try:
        analysis = await analyze_resume_skills(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        )
    except AIAnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await _save_ai_result(resume_id, user, "skills", analysis)


@router.post("/{resume_id}/experience-analysis")
async def analyze_experience(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before analyzing its experience.")

    settings = get_settings()
    try:
        analysis = await analyze_resume_experience(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        )
    except AIAnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await _save_ai_result(resume_id, user, "experience", analysis)


@router.post("/{resume_id}/education-analysis")
async def analyze_education(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before analyzing its education.")

    settings = get_settings()
    try:
        analysis = await analyze_resume_education(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        )
    except AIAnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await _save_ai_result(resume_id, user, "education", analysis)


@router.post("/{resume_id}/project-analysis")
async def analyze_projects(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before analyzing its projects.")

    settings = get_settings()
    try:
        analysis = await analyze_resume_projects(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        )
    except AIAnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await _save_ai_result(resume_id, user, "projects", analysis)


@router.post("/{resume_id}/strengths-analysis")
async def analyze_strengths(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before analyzing its strengths.")

    settings = get_settings()
    try:
        analysis = await analyze_resume_strengths(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        )
    except AIAnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await _save_ai_result(resume_id, user, "strengths", analysis)


@router.post("/{resume_id}/weaknesses-analysis")
async def analyze_weaknesses(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before analyzing its weaknesses.")

    settings = get_settings()
    try:
        analysis = await analyze_resume_weaknesses(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        )
    except AIAnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await _save_ai_result(resume_id, user, "weaknesses", analysis)


@router.post("/{resume_id}/summary-analysis")
async def analyze_resume_summary(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before generating its summary.")

    settings = get_settings()
    try:
        result = await generate_resume_summary(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        )
    except AIAnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await _save_ai_result(resume_id, user, "summary", result)


@router.post("/{resume_id}/full-analysis")
async def analyze_full_resume_route(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before running its analysis.")

    settings = get_settings()
    try:
        result = await analyze_full_resume(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        )
    except AIAnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await _save_ai_result(resume_id, user, "full_resume", result)


@router.post("/{resume_id}/improvement-suggestions")
async def suggest_resume_improvements(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    if not doc.get("parsed"):
        raise HTTPException(
            status_code=409,
            detail="Parse this resume before generating improvement suggestions.",
        )

    settings = get_settings()
    try:
        result = await generate_improvement_suggestions(
            doc["parsed"],
            settings.ai_api_key,
            settings.ai_model_name,
        )
    except AIAnalysisError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return await _save_ai_result(resume_id, user, "improvement_suggestions", result)


# NEW: re-run parsing on a resume that was uploaded before this feature existed
@router.post("/{resume_id}/parse")
async def reparse(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(doc["file_url"])
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Could not re-download the file from Cloudinary.")
    try:
        raw_text = await run_in_threadpool(extract_text, resp.content, doc["file_type"])
        parsed = await run_in_threadpool(parse_resume, raw_text)
    except ParseError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    update_result = await get_db().resumes.update_one(
        {"_id": doc["_id"], "user_id": user["_id"]},
        {"$set": {"parsed": parsed, "ai_results": {}}},
    )
    if update_result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return {"id": resume_id, "parsed": parsed}


@router.delete("/{resume_id}", status_code=204)
async def delete(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    try:
        await run_in_threadpool(delete_resume, doc["cloudinary_public_id"])
    except Exception as exc:  # even if Cloudinary cleanup fails, still remove the record
        log.warning("Cloudinary delete failed: %s", exc)
    await get_db().resumes.delete_one({"_id": doc["_id"]})