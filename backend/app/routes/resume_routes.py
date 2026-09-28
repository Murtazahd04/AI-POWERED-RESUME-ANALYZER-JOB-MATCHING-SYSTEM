import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pymongo import DESCENDING

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
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


@router.delete("/{resume_id}", status_code=204)
async def delete(resume_id: str, user: dict = Depends(get_current_user)):
    doc = await _get_owned(resume_id, user)
    try:
        await run_in_threadpool(delete_resume, doc["cloudinary_public_id"])
    except Exception as exc:  # even if Cloudinary cleanup fails, still remove the record
        log.warning("Cloudinary delete failed: %s", exc)
    await get_db().resumes.delete_one({"_id": doc["_id"]})