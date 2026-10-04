"""AI extraction of resume text into the application's validated resume schema."""
import json
import re
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from ..schemas import ParsedResumeUpdate
from .ai_analysis_service import AIAnalysisError


PARSER_SYSTEM_PROMPT = """You extract resume facts into JSON. Use only facts explicitly present in
the supplied resume text. Do not infer, improve, complete, or fabricate any detail. Return exactly
one JSON object matching this schema:
{
  "name": string|null,
  "contact": {"email": string|null, "phone": string|null, "linkedin": string|null, "github": string|null},
  "summary": string|null,
  "education": [{"degree": string|null, "institution": string|null, "year": string|null}],
  "experience": [{"title": string|null, "date_range": string, "highlights": [string], "technologies": [string]}],
  "total_experience_years": number,
  "projects": [{"name": string, "description": [string], "technologies": [string]}],
  "certifications": [string],
  "skills": {"technical": [string], "soft": [string]}
}
For missing scalar fields use null. For missing lists use []. Use 0 for unknown total_experience_years.
Do not add keys that are not in the schema."""


def prepare_resume_text_for_ai(raw_text: str, max_chars: int) -> str:
    """Keep extracted resume text only; never send file bytes, metadata, or stored analysis."""
    normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", normalized)
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    if not normalized:
        raise AIAnalysisError("The resume has no extractable text.", 422)
    if max_chars < 1:
        raise AIAnalysisError("AI parsing text limit is misconfigured.", 503)
    if len(normalized) > max_chars:
        raise AIAnalysisError(
            f"This resume is too long for AI parsing ({max_chars:,} character limit). Choose spaCy parsing instead.",
            413,
        )
    return normalized


async def parse_resume_with_ai(raw_text: str, api_key: str, model_name: str, max_chars: int = 40_000) -> dict:
    resume_text = prepare_resume_text_for_ai(raw_text, max_chars)
    if not api_key.strip():
        raise AIAnalysisError("AI parsing is not configured. Set AI_API_KEY in the backend environment.", 503)
    if not model_name.strip():
        raise AIAnalysisError("AI parsing model is not configured.", 503)

    url = "https://generativelanguage.googleapis.com/v1beta/models/" f"{quote(model_name.strip(), safe='-_.')}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": PARSER_SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": resume_text}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
    }
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(url, params={"key": api_key}, json=payload)
    except httpx.TimeoutException as exc:
        raise AIAnalysisError("AI parsing provider timed out. Please try again.", 504) from exc
    except httpx.RequestError as exc:
        raise AIAnalysisError("Could not reach the AI parsing provider. Please try again.", 502) from exc

    if response.status_code == 429:
        raise AIAnalysisError("AI parsing provider is rate-limiting requests. Please try again later.", 503)
    if response.status_code in {404, 503}:
        raise AIAnalysisError("AI parsing model is unavailable. Check the AI configuration and try again.", 503)
    if response.is_error:
        raise AIAnalysisError(f"AI parsing provider returned HTTP {response.status_code}.", 502)

    try:
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        result = json.loads(text)
        return ParsedResumeUpdate.model_validate(result).model_dump(mode="json")
    except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
        raise AIAnalysisError("AI provider returned an invalid resume parse.") from exc
