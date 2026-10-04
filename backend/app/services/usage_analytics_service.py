"""Usage summaries with explicit attribution for exact and allocated values."""
from collections import defaultdict


_DIRECT_SECTION_OPERATIONS = {
    "skills", "experience", "education", "projects", "strengths", "weaknesses", "summary",
}


def _sum_known(events: list[dict], field: str) -> float | int | None:
    values = [event[field] for event in events if event.get(field) is not None]
    if not values:
        return None
    total = sum(values)
    return round(total, 12) if isinstance(total, float) else total


def section_usage(events: list[dict]) -> list[dict]:
    """Group usage by section without inventing a split for combined requests."""
    grouped: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        grouped[event["operation"]].append(event)

    summaries = []
    for operation, entries in sorted(grouped.items()):
        direct = operation in _DIRECT_SECTION_OPERATIONS or operation == "improvement_suggestions"
        summaries.append({
            "section": operation,
            "request_count": len(entries),
            "provider_reported_usage_count": sum(bool(e.get("provider_reported_usage")) for e in entries),
            "input_tokens": _sum_known(entries, "input_tokens"),
            "output_tokens": _sum_known(entries, "output_tokens"),
            "estimated_total_cost_usd": _sum_known(entries, "estimated_total_cost_usd"),
            "usage_attribution": (
                "provider_reported_section_request"
                if direct
                else "provider_reported_combined_request_no_section_allocation"
            ),
        })
    return summaries


def user_recommendation_costs(events: list[dict]) -> list[dict]:
    """Return per-user costs for generated improvement recommendations.

    Individual recommendation costs are allocations of each generating request's total
    estimated cost; providers report usage at request level, not recommendation level.
    """
    grouped: dict[object, list[dict]] = defaultdict(list)
    for event in events:
        if (
            event.get("operation") in {"improvement_suggestions", "full_resume"}
            and event.get("status") == "succeeded"
            and event.get("user_id") is not None
            and event.get("recommendation_count") is not None
        ):
            grouped[event["user_id"]].append(event)

    summaries = []
    for user_id, entries in grouped.items():
        costed_entries = [e for e in entries if e.get("estimated_total_cost_usd") is not None]
        costed_recommendations = sum(e.get("recommendation_count", 0) for e in costed_entries)
        total_cost = _sum_known(costed_entries, "estimated_total_cost_usd")
        summaries.append({
            "user_id": user_id,
            "recommendation_request_count": len(entries),
            "recommendation_count": sum(e.get("recommendation_count", 0) for e in entries),
            "costed_recommendation_count": costed_recommendations,
            "estimated_total_cost_usd": total_cost,
            "estimated_cost_per_recommendation_usd": (
                round(total_cost / costed_recommendations, 12)
                if total_cost is not None and costed_recommendations
                else None
            ),
            "cost_attribution": _attribution_label(entries),
        })
    return summaries


def _attribution_label(entries: list[dict]) -> str:
    labels = {entry.get("recommendation_cost_attribution", "allocated_from_request_total") for entry in entries}
    return labels.pop() if len(labels) == 1 else "allocated_from_multiple_request_types"


def dashboard_metrics(events: list[dict]) -> dict:
    """Build the admin dashboard's aggregate metrics from usage events."""
    successful = [event for event in events if event.get("status") == "succeeded"]
    model_groups: dict[str, list[dict]] = defaultdict(list)
    for event in events:
        model_groups[event.get("model", "unknown")].append(event)

    models = []
    for model, entries in sorted(model_groups.items()):
        models.append({
            "model": model,
            "request_count": len(entries),
            "successful_request_count": sum(e.get("status") == "succeeded" for e in entries),
            "provider_reported_usage_count": sum(bool(e.get("provider_reported_usage")) for e in entries),
            "input_tokens": _sum_known(entries, "input_tokens"),
            "output_tokens": _sum_known(entries, "output_tokens"),
            "estimated_total_cost_usd": _sum_known(entries, "estimated_total_cost_usd"),
        })

    return {
        "summary": {
            "analyzed_resume_count": len({event.get("resume_id") for event in successful if event.get("resume_id")}),
            "successful_analysis_request_count": len(successful),
            "model_count": len(model_groups),
            "input_tokens": _sum_known(events, "input_tokens"),
            "output_tokens": _sum_known(events, "output_tokens"),
            "estimated_total_cost_usd": _sum_known(events, "estimated_total_cost_usd"),
        },
        "models": models,
        "sections": section_usage(events),
        "recommendation_costs": user_recommendation_costs(events),
    }
