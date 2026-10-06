"""
Skill Gap API (Feature 9).

POST /api/skill-gap/analyze   {resume_id, role}  -> analyse a typed role against a resume, save, return it
GET  /api/skill-gap/latest                       -> the user's most recent analysis (or null)
GET  /api/skill-gap/roles                        -> role names for the suggestion list
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..services import skill_gap_service
from ..utils import now, to_object_id

router = APIRouter(prefix="/api/skill-gap", tags=["skill-gap"])


class AnalyzeIn(BaseModel):
    resume_id: str
    role: str = Field(min_length=2, max_length=80)


def _iso(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


@router.get("/roles")
async def roles(user: dict = Depends(get_current_user)):
    return skill_gap_service.list_roles()


@router.post("/analyze")
async def analyze(body: AnalyzeIn, user: dict = Depends(get_current_user)):
    db = get_db()
    resume = await db.resumes.find_one({"_id": to_object_id(body.resume_id), "user_id": user["_id"]})
    if resume is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    if not resume.get("parsed"):
        raise HTTPException(status_code=409, detail="Parse this resume before running a skill gap analysis.")

    settings = get_settings()
    skill_gap_service.configure_llm(
        getattr(settings, "ai_api_key", None),
        getattr(settings, "ai_model_name", None),
    )

    try:
        result = await run_in_threadpool(skill_gap_service.analyze_role, resume["parsed"], body.role)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    role_key = " ".join(body.role.lower().split())
    created_at = now()
    doc = {
        **result,
        "user_id": user["_id"],
        "resume_id": body.resume_id,
        "role_key": role_key,
        "resume_filename": resume.get("filename", ""),
        "created_at": created_at,
    }
    await db.skill_gaps.update_one(
        {"user_id": user["_id"], "resume_id": body.resume_id, "role_key": role_key},
        {"$set": doc},
        upsert=True,
    )

    for hidden in ("user_id", "role_key"):
        doc.pop(hidden, None)
    doc["created_at"] = _iso(created_at)
    return doc


@router.get("/latest")
async def latest(user: dict = Depends(get_current_user)):
    doc = await get_db().skill_gaps.find_one({"user_id": user["_id"]}, sort=[("created_at", -1)])
    if doc is None:
        return None
    for hidden in ("_id", "user_id", "role_key"):
        doc.pop(hidden, None)
    doc["created_at"] = _iso(doc.get("created_at"))
    return doc