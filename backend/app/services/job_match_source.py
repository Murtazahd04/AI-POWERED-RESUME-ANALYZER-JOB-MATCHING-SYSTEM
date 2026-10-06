"""Fetches live job postings from Adzuna for job matching.

Needs (in backend/.env, or as attributes on your Settings class):
    ADZUNA_APP_ID, ADZUNA_APP_KEY
    ADZUNA_COUNTRY=in        (in = India; this is what stops you getting UK jobs)
"""
import os
import re

import httpx

try:  # optional: only used if your Settings class doesn't already load .env
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from ..config import get_settings

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs"


class JobSourceError(Exception):
    """Raised when the job source can't be reached or rejects the request."""


def _setting(attr: str, env: str, default: str = "") -> str:
    """Read from Settings if it has the attribute, otherwise from the environment."""
    try:
        value = getattr(get_settings(), attr, None)
    except Exception:
        value = None
    return str(value or os.getenv(env) or default).strip()


def country() -> str:
    return _setting("adzuna_country", "ADZUNA_COUNTRY", "in").lower() or "in"


def _clean(text: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", text).strip()


def _normalize(j: dict) -> dict:
    return {
        "id": str(j.get("id")),
        "title": _clean(j.get("title")),
        "company": _clean((j.get("company") or {}).get("display_name")) or "Company not listed",
        "location": _clean((j.get("location") or {}).get("display_name")) or "India",
        "description": _clean(j.get("description")),
        "url": j.get("redirect_url"),
        "posted": j.get("created"),
        "salary_min": j.get("salary_min"),
        "salary_max": j.get("salary_max"),
        "salary_is_estimate": str(j.get("salary_is_predicted")) == "1",
        "contract_time": j.get("contract_time"),
    }


async def search_adzuna(what: str, where: str | None = None, limit: int = 20) -> list[dict]:
    app_id = _setting("adzuna_app_id", "ADZUNA_APP_ID")
    app_key = _setting("adzuna_app_key", "ADZUNA_APP_KEY")
    if not app_id or not app_key:
        raise JobSourceError("Adzuna keys are missing. Set ADZUNA_APP_ID and ADZUNA_APP_KEY in backend/.env.")

    params = {"app_id": app_id, "app_key": app_key, "what": what, "results_per_page": limit}
    if where:
        params["where"] = where

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{ADZUNA_BASE}/{country()}/search/1", params=params)
    except httpx.HTTPError as exc:
        raise JobSourceError("Could not reach Adzuna. Check your internet connection.") from exc

    if resp.status_code in (401, 403):
        raise JobSourceError("Adzuna rejected the API keys. Check ADZUNA_APP_ID and ADZUNA_APP_KEY.")
    if resp.status_code == 429:
        raise JobSourceError("Adzuna rate limit reached. Wait a few minutes and try again.")
    if resp.status_code != 200:
        raise JobSourceError(f"Adzuna returned an error ({resp.status_code}).")

    return [_normalize(j) for j in resp.json().get("results", [])]