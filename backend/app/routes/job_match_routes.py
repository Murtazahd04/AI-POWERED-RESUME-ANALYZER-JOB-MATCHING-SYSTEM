import hashlib
import json
import time

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..services.job_match_source import JobSourceError
from ..services.job_matching_service import NotEnoughData, match_jobs
from ..utils import to_object_id

router = APIRouter(prefix="/api/resumes", tags=["job matching"])

CACHE_SECONDS = 3 * 60 * 60  # reuse results for 3 hours to protect the Adzuna and Gemini free limits


async def _get_owned(resume_id: str, user: dict) -> dict:
    doc = await get_db().resumes.find_one({"_id": to_object_id(resume_id), "user_id": user["_id"]})
    if doc is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return doc


@router.get("/{resume_id}/job-matches")
async def job_matches(
    resume_id: str,
    where: str | None = Query(default=None, max_length=60),
    refresh: bool = False,
    user: dict = Depends(get_current_user),
):
    doc = await _get_owned(resume_id, user)
    parsed = doc.get("parsed")
    if not parsed:
        raise HTTPException(status_code=409, detail="Parse this resume first, then try again.")

    where = (where or "").strip() or None
    fingerprint = hashlib.sha256(json.dumps(parsed, sort_keys=True, default=str).encode()).hexdigest()[:16]

    db = get_db()
    cache = await db.job_matches.find_one({"resume_id": doc["_id"]})
    if (
        cache and not refresh
        and cache.get("fingerprint") == fingerprint
        and cache.get("where") == where
        and time.time() - cache.get("ts", 0) < CACHE_SECONDS
    ):
        saved = {k: v for k, v in cache["result"].items() if k != "ai_usage"}  # tokens were spent on the original call only
        return {**saved, "cached": True}

    settings = get_settings()
    try:
        result = await match_jobs(
            parsed,
            where,
            getattr(settings, "ai_api_key", "") or "",
            getattr(settings, "ai_model_name", "") or "",
        )
    except NotEnoughData as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except JobSourceError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    await db.job_matches.replace_one(
        {"resume_id": doc["_id"]},
        {"resume_id": doc["_id"], "fingerprint": fingerprint, "where": where, "ts": time.time(), "result": result},
        upsert=True,
    )
    return {**result, "cached": False}