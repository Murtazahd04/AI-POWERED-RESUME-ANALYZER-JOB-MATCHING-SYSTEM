"""Gemini-backed resume skills analysis."""
import json
from typing import Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .ai_prompt_service import (
    EDUCATION_ANALYSIS_SYSTEM_PROMPT,
    EXPERIENCE_ANALYSIS_SYSTEM_PROMPT,
    IMPROVEMENT_SUGGESTIONS_SYSTEM_PROMPT,
    PROJECT_ANALYSIS_SYSTEM_PROMPT,
    RESUME_STRENGTHS_SYSTEM_PROMPT,
    RESUME_ANALYSIS_SYSTEM_PROMPT,
    RESUME_SUMMARY_SYSTEM_PROMPT,
    RESUME_WEAKNESSES_SYSTEM_PROMPT,
    SKILL_ANALYSIS_SYSTEM_PROMPT,
    build_education_analysis_prompt,
    build_experience_analysis_prompt,
    build_improvement_suggestions_prompt,
    build_project_analysis_prompt,
    build_resume_strengths_prompt,
    build_resume_analysis_messages,
    build_resume_summary_prompt,
    build_resume_weaknesses_prompt,
    build_skill_analysis_prompt,
)


class SkillAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    identified_skills: list[str] = Field(max_length=100)
    strengths: list[str] = Field(max_length=30)
    gaps: list[str] = Field(max_length=30)


class ExperienceAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment: str = Field(max_length=3000)
    relevant_strengths: list[str] = Field(max_length=30)
    gaps: list[str] = Field(max_length=30)


class EducationAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment: str = Field(max_length=3000)
    relevant_details: list[str] = Field(max_length=30)


class CertificationAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment: str = Field(max_length=3000)
    relevant_details: list[str] = Field(max_length=30)


class ProjectAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment: str = Field(max_length=3000)
    project_highlights: list[str] = Field(max_length=30)


class ResumeStrengths(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strengths: list[str] = Field(max_length=30)


class ResumeWeaknesses(BaseModel):
    model_config = ConfigDict(extra="forbid")

    weaknesses: list[str] = Field(max_length=30)


class ResumeSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1200)


class ImprovementSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: Literal[
        "Summary",
        "Skills",
        "Experience",
        "Education",
        "Projects",
        "Certifications",
        "Strengths",
        "Weaknesses",
        "Formatting & clarity",
        "General",
    ]
    priority: Literal["high", "medium", "low"]
    suggestion: str = Field(min_length=1, max_length=1000)
    reason: str = Field(min_length=1, max_length=1000)


class ImprovementSuggestions(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suggestions: list[ImprovementSuggestion] = Field(max_length=10)


class FullResumeAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skills_analysis: SkillAnalysis
    experience_analysis: ExperienceAnalysis
    education_analysis: EducationAnalysis
    certification_analysis: CertificationAnalysis
    project_analysis: ProjectAnalysis
    strengths: list[str] = Field(max_length=30)
    weaknesses: list[str] = Field(max_length=30)
    summary: str = Field(min_length=1, max_length=1200)
    improvement_suggestions: list[ImprovementSuggestion] = Field(max_length=10)


class AIAnalysisError(Exception):
    """An expected provider/configuration error that can be shown to the API caller."""

    def __init__(self, detail: str, status_code: int = 502):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


async def _request_structured_analysis(
    api_key: str,
    model_name: str,
    system_prompt: str,
    user_prompt: str,
) -> dict:
    if not api_key.strip():
        raise AIAnalysisError("AI analysis is not configured. Set AI_API_KEY in the backend environment.", 503)
    if not model_name.strip():
        raise AIAnalysisError("AI analysis model is not configured.", 503)

    model_path = quote(model_name.strip(), safe="-_.")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_path}:generateContent"
    )
    payload = {
        "systemInstruction": {
            "parts": [{"text": system_prompt}],
        },
        "contents": [{
            "role": "user",
            "parts": [{"text": user_prompt}],
        }],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                url,
                params={"key": api_key},
                json=payload,
            )
    except httpx.TimeoutException as exc:
        raise AIAnalysisError("AI analysis provider timed out. Please try again.", 504) from exc
    except httpx.RequestError as exc:
        raise AIAnalysisError("Could not reach the AI analysis provider. Please try again.", 502) from exc

    if response.status_code == 429:
        raise AIAnalysisError("AI analysis provider is rate-limiting requests. Please try again later.", 503)
    if response.status_code == 404:
        raise AIAnalysisError(
            f"Gemini model '{model_name.strip()}' is unavailable for this API key. "
            "Set AI_MODEL_NAME to a model enabled for your key, such as gemini-3.5-flash-lite.",
            503,
        )
    if response.status_code == 503:
        raise AIAnalysisError(
            "Gemini is temporarily overloaded. Please try again in a few minutes.",
            503,
        )
    if response.is_error:
        raise AIAnalysisError(
            f"AI analysis provider returned HTTP {response.status_code}. Check the AI configuration and try again.",
            502,
        )

    try:
        candidates = response.json()["candidates"]
        text = candidates[0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
        raise AIAnalysisError("AI provider returned an invalid analysis response.") from exc


async def analyze_resume_skills(
    parsed_resume: dict,
    api_key: str,
    model_name: str,
) -> dict:
    parsed_result = await _request_structured_analysis(
        api_key,
        model_name,
        SKILL_ANALYSIS_SYSTEM_PROMPT,
        build_skill_analysis_prompt(parsed_resume),
    )
    try:
        return SkillAnalysis.model_validate(parsed_result).model_dump()
    except (TypeError, ValueError, ValidationError) as exc:
        raise AIAnalysisError("AI provider returned an invalid skill analysis response.") from exc


async def analyze_resume_experience(
    parsed_resume: dict,
    api_key: str,
    model_name: str,
) -> dict:
    parsed_result = await _request_structured_analysis(
        api_key,
        model_name,
        EXPERIENCE_ANALYSIS_SYSTEM_PROMPT,
        build_experience_analysis_prompt(parsed_resume),
    )
    try:
        return ExperienceAnalysis.model_validate(parsed_result).model_dump()
    except (TypeError, ValueError, ValidationError) as exc:
        raise AIAnalysisError("AI provider returned an invalid experience analysis response.") from exc


async def analyze_resume_education(
    parsed_resume: dict,
    api_key: str,
    model_name: str,
) -> dict:
    parsed_result = await _request_structured_analysis(
        api_key,
        model_name,
        EDUCATION_ANALYSIS_SYSTEM_PROMPT,
        build_education_analysis_prompt(parsed_resume),
    )
    try:
        return EducationAnalysis.model_validate(parsed_result).model_dump()
    except (TypeError, ValueError, ValidationError) as exc:
        raise AIAnalysisError("AI provider returned an invalid education analysis response.") from exc


async def analyze_resume_projects(
    parsed_resume: dict,
    api_key: str,
    model_name: str,
) -> dict:
    parsed_result = await _request_structured_analysis(
        api_key,
        model_name,
        PROJECT_ANALYSIS_SYSTEM_PROMPT,
        build_project_analysis_prompt(parsed_resume),
    )
    try:
        return ProjectAnalysis.model_validate(parsed_result).model_dump()
    except (TypeError, ValueError, ValidationError) as exc:
        raise AIAnalysisError("AI provider returned an invalid project analysis response.") from exc


async def analyze_resume_strengths(
    parsed_resume: dict,
    api_key: str,
    model_name: str,
) -> dict:
    parsed_result = await _request_structured_analysis(
        api_key,
        model_name,
        RESUME_STRENGTHS_SYSTEM_PROMPT,
        build_resume_strengths_prompt(parsed_resume),
    )
    try:
        return ResumeStrengths.model_validate(parsed_result).model_dump()
    except (TypeError, ValueError, ValidationError) as exc:
        raise AIAnalysisError("AI provider returned an invalid resume strengths response.") from exc


async def analyze_resume_weaknesses(
    parsed_resume: dict,
    api_key: str,
    model_name: str,
) -> dict:
    parsed_result = await _request_structured_analysis(
        api_key,
        model_name,
        RESUME_WEAKNESSES_SYSTEM_PROMPT,
        build_resume_weaknesses_prompt(parsed_resume),
    )
    try:
        return ResumeWeaknesses.model_validate(parsed_result).model_dump()
    except (TypeError, ValueError, ValidationError) as exc:
        raise AIAnalysisError("AI provider returned an invalid resume weaknesses response.") from exc


async def generate_resume_summary(
    parsed_resume: dict,
    api_key: str,
    model_name: str,
) -> dict:
    parsed_result = await _request_structured_analysis(
        api_key,
        model_name,
        RESUME_SUMMARY_SYSTEM_PROMPT,
        build_resume_summary_prompt(parsed_resume),
    )
    try:
        return ResumeSummary.model_validate(parsed_result).model_dump()
    except (TypeError, ValueError, ValidationError) as exc:
        raise AIAnalysisError("AI provider returned an invalid resume summary response.") from exc


async def generate_improvement_suggestions(
    parsed_resume: dict,
    api_key: str,
    model_name: str,
) -> dict:
    parsed_result = await _request_structured_analysis(
        api_key,
        model_name,
        IMPROVEMENT_SUGGESTIONS_SYSTEM_PROMPT,
        build_improvement_suggestions_prompt(parsed_resume),
    )
    try:
        return ImprovementSuggestions.model_validate(parsed_result).model_dump()
    except (TypeError, ValueError, ValidationError) as exc:
        raise AIAnalysisError("AI provider returned invalid improvement suggestions.") from exc


async def analyze_full_resume(
    parsed_resume: dict,
    api_key: str,
    model_name: str,
) -> dict:
    messages = build_resume_analysis_messages(parsed_resume)
    parsed_result = await _request_structured_analysis(
        api_key,
        model_name,
        RESUME_ANALYSIS_SYSTEM_PROMPT,
        messages[1]["content"],
    )
    try:
        return FullResumeAnalysis.model_validate(parsed_result).model_dump()
    except (TypeError, ValueError, ValidationError) as exc:
        raise AIAnalysisError("AI provider returned an invalid complete resume analysis response.") from exc
