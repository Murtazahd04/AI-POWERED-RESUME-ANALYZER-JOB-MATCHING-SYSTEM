from fastapi import APIRouter
from ..database import get_db

router = APIRouter(tags=["health"])


@router.get("/api/health")
async def health():
    try:
        await get_db().command("ping")
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        return {"status": "degraded", "database": "unreachable", "error": str(exc)}