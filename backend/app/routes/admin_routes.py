from datetime import date, datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_db
from ..deps import get_current_admin
from ..services.usage_analytics_service import dashboard_metrics
from ..utils import serialize

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def _enrich_historical_full_resume_events(events: list[dict]) -> None:
    """Fill recommendation metadata for events created before it was recorded."""
    missing = [event for event in events if event.get("operation") == "full_resume" and "recommendation_count" not in event]
    if not missing:
        return
    resume_ids = list({event["resume_id"] for event in missing if event.get("resume_id")})
    resumes = {
        resume["_id"]: resume
        async for resume in get_db().resumes.find(
            {"_id": {"$in": resume_ids}},
            {"ai_results.full_resume.result.improvement_suggestions": 1},
        )
    }
    for event in missing:
        suggestions = resumes.get(event.get("resume_id"), {}).get("ai_results", {}).get("full_resume", {}).get("result", {}).get("improvement_suggestions", [])
        count = len(suggestions)
        event["recommendation_count"] = count
        event["recommendation_cost_attribution"] = "allocated_from_combined_full_resume_request_total"
        total = event.get("estimated_total_cost_usd")
        event["estimated_cost_per_recommendation_usd"] = round(total / count, 12) if total is not None and count else None


@router.get("/access")
async def admin_access(admin: dict = Depends(get_current_admin)):
    """Confirm the authenticated user may access admin-only APIs."""
    return serialize(admin, drop=("password_hash",))


@router.get("/analytics")
async def analytics(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    _admin: dict = Depends(get_current_admin),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date must be on or before end_date.")

    timestamp_query = {}
    if start_date:
        timestamp_query["$gte"] = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    if end_date:
        timestamp_query["$lt"] = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    query = {"timestamp": timestamp_query} if timestamp_query else {}
    events = [event async for event in get_db().ai_usage_events.find(query)]
    await _enrich_historical_full_resume_events(events)
    metrics = dashboard_metrics(events)
    for row in metrics["recommendation_costs"]:
        row["user_id"] = str(row["user_id"])
    return {
        "period": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
        **metrics,
    }
