import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.services.ai_analysis_service import (
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
from app.services.ai_prompt_service import (
    EDUCATION_ANALYSIS_SYSTEM_PROMPT,
    EXPERIENCE_ANALYSIS_SYSTEM_PROMPT,
    PROJECT_ANALYSIS_SYSTEM_PROMPT,
    RESUME_STRENGTHS_SYSTEM_PROMPT,
    RESUME_WEAKNESSES_SYSTEM_PROMPT,
    RESUME_SUMMARY_SYSTEM_PROMPT,
    IMPROVEMENT_SUGGESTIONS_SYSTEM_PROMPT,
)


class AnalyzeResumeSkillsTests(unittest.IsolatedAsyncioTestCase):
    async def test_calls_gemini_with_json_mode_and_validates_result(self):
        expected = {
            "identified_skills": ["Python"],
            "strengths": ["Uses Python in a resume project."],
            "gaps": ["Role-specific gaps cannot be determined without a target role."],
        }
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(expected)}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            result = await analyze_resume_skills(
                {"skills": {"technical": ["Python"]}},
                "test-api-key",
                "gemini-test-model",
            )

        self.assertEqual(result, expected)
        call = client.post.await_args
        self.assertIn("gemini-test-model:generateContent", call.args[0])
        self.assertEqual(call.kwargs["params"], {"key": "test-api-key"})
        self.assertEqual(call.kwargs["json"]["generationConfig"]["responseMimeType"], "application/json")

    async def test_missing_api_key_returns_configuration_error_without_request(self):
        with patch("app.services.ai_analysis_service.httpx.AsyncClient") as client_class:
            with self.assertRaises(AIAnalysisError) as context:
                await analyze_resume_skills({}, "", "gemini-test-model")

        self.assertEqual(context.exception.status_code, 503)
        client_class.assert_not_called()

    async def test_invalid_provider_json_shape_is_reported(self):
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"identified_skills": []}'}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            with self.assertRaises(AIAnalysisError) as context:
                await analyze_resume_skills({}, "test-api-key", "gemini-test-model")

        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("invalid skill analysis response", context.exception.detail)

    async def test_unavailable_model_returns_actionable_configuration_error(self):
        response = httpx.Response(
            404,
            json={"error": {"message": "This model is no longer available."}},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            with self.assertRaises(AIAnalysisError) as context:
                await analyze_resume_skills({}, "test-api-key", "gemini-2.5-flash")

        self.assertEqual(context.exception.status_code, 503)
        self.assertIn("gemini-2.5-flash", context.exception.detail)
        self.assertIn("gemini-3.5-flash-lite", context.exception.detail)

    async def test_provider_overload_has_retryable_error(self):
        response = httpx.Response(
            503,
            json={"error": {"message": "Temporary overload."}},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            with self.assertRaises(AIAnalysisError) as context:
                await analyze_resume_skills({}, "test-api-key", "gemini-3.5-flash-lite")

        self.assertEqual(context.exception.status_code, 503)
        self.assertIn("temporarily overloaded", context.exception.detail)


class AnalyzeFullResumeTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_validated_full_analysis_from_one_provider_request(self):
        expected = {
            "skills_analysis": {
                "identified_skills": ["Python"],
                "strengths": ["Uses Python in project work."],
                "gaps": ["Role-specific gaps require a target job."],
            },
            "experience_analysis": {
                "assessment": "The resume describes relevant work.",
                "relevant_strengths": ["Automated weekly reporting."],
                "gaps": ["Impact is not quantified."],
            },
            "education_analysis": {
                "assessment": "Education is clearly identified.",
                "relevant_details": ["BSc in Data Science."],
            },
            "certification_analysis": {
                "assessment": "The resume includes a relevant certification.",
                "relevant_details": ["Cloud Fundamentals."],
            },
            "project_analysis": {
                "assessment": "Projects demonstrate applied skills.",
                "project_highlights": ["Built a sales dashboard."],
            },
            "strengths": ["Evidence of practical data analysis."],
            "weaknesses": ["Some experience outcomes lack metrics."],
            "summary": "Data analyst with Python project experience.",
            "improvement_suggestions": [{
                "section": "Experience",
                "priority": "medium",
                "suggestion": "Add verified outcome measures to relevant bullets.",
                "reason": "The current bullets describe tasks but not their impact.",
            }],
        }
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(expected)}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            result = await analyze_full_resume(
                {"skills": {"technical": ["Python"]}, "contact": {"email": "private@example.com"}},
                "test-api-key",
                "gemini-test-model",
            )

        self.assertEqual(result, expected)
        client.post.assert_awaited_once()
        self.assertNotIn("private@example.com", client.post.await_args.kwargs["json"]["contents"][0]["parts"][0]["text"])

    async def test_rejects_invalid_nested_full_analysis(self):
        invalid = {"summary": "Only a summary."}
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(invalid)}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            with self.assertRaises(AIAnalysisError) as context:
                await analyze_full_resume({}, "test-api-key", "gemini-test-model")

        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("invalid complete resume analysis", context.exception.detail)


class AnalyzeResumeExperienceTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_validated_experience_analysis(self):
        expected = {
            "assessment": "Experience includes clear responsibility but limited outcome detail.",
            "relevant_strengths": ["Automated recurring reporting with Python."],
            "gaps": ["Add quantified impact where available."],
        }
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(expected)}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            result = await analyze_resume_experience(
                {"experience": [{"title": "Data Intern"}]},
                "test-api-key",
                "gemini-test-model",
            )

        self.assertEqual(result, expected)
        self.assertEqual(
            client.post.await_args.kwargs["json"]["systemInstruction"]["parts"][0]["text"],
            EXPERIENCE_ANALYSIS_SYSTEM_PROMPT,
        )
        self.assertIn(
            '"experience"',
            client.post.await_args.kwargs["json"]["contents"][0]["parts"][0]["text"],
        )

    async def test_rejects_unstructured_experience_response(self):
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"assessment": "Only assessment"}'}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            with self.assertRaises(AIAnalysisError) as context:
                await analyze_resume_experience({}, "test-api-key", "gemini-test-model")

        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("invalid experience analysis response", context.exception.detail)


class AnalyzeResumeEducationTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_validated_education_analysis(self):
        expected = {
            "assessment": "The degree and institution are stated, but no graduation date is provided.",
            "relevant_details": ["The resume lists a BSc from Example University."],
        }
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(expected)}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            result = await analyze_resume_education(
                {"education": [{"degree": "BSc", "institution": "Example University"}]},
                "test-api-key",
                "gemini-test-model",
            )

        self.assertEqual(result, expected)
        request = client.post.await_args.kwargs["json"]
        self.assertEqual(
            request["systemInstruction"]["parts"][0]["text"],
            EDUCATION_ANALYSIS_SYSTEM_PROMPT,
        )
        self.assertIn('"Example University"', request["contents"][0]["parts"][0]["text"])

    async def test_rejects_unstructured_education_response(self):
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"assessment": "Only assessment"}'}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            with self.assertRaises(AIAnalysisError) as context:
                await analyze_resume_education({}, "test-api-key", "gemini-test-model")

        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("invalid education analysis response", context.exception.detail)


class AnalyzeResumeProjectsTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_validated_project_analysis(self):
        expected = {
            "assessment": "The project explains its purpose and lists its implementation technologies.",
            "project_highlights": ["Built an inventory dashboard using React and MongoDB."],
        }
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(expected)}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            result = await analyze_resume_projects(
                {"projects": [{"name": "Inventory tracker", "technologies": ["React", "MongoDB"]}]},
                "test-api-key",
                "gemini-test-model",
            )

        self.assertEqual(result, expected)
        request = client.post.await_args.kwargs["json"]
        self.assertEqual(
            request["systemInstruction"]["parts"][0]["text"],
            PROJECT_ANALYSIS_SYSTEM_PROMPT,
        )
        self.assertIn('"Inventory tracker"', request["contents"][0]["parts"][0]["text"])

    async def test_rejects_unstructured_project_response(self):
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"assessment": "Only assessment"}'}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            with self.assertRaises(AIAnalysisError) as context:
                await analyze_resume_projects({}, "test-api-key", "gemini-test-model")

        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("invalid project analysis response", context.exception.detail)


class AnalyzeResumeStrengthsTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_validated_resume_strengths(self):
        expected = {
            "strengths": [
                "Applied Python to automate reporting during a developer internship.",
                "Built projects using React and MongoDB.",
            ],
        }
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(expected)}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            result = await analyze_resume_strengths(
                {"skills": {"technical": ["Python"]}, "experience": [], "projects": []},
                "test-api-key",
                "gemini-test-model",
            )

        self.assertEqual(result, expected)
        request = client.post.await_args.kwargs["json"]
        self.assertEqual(
            request["systemInstruction"]["parts"][0]["text"],
            RESUME_STRENGTHS_SYSTEM_PROMPT,
        )
        self.assertIn('"Python"', request["contents"][0]["parts"][0]["text"])

    async def test_rejects_unstructured_strengths_response(self):
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"strengths": "not a list"}'}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            with self.assertRaises(AIAnalysisError) as context:
                await analyze_resume_strengths({}, "test-api-key", "gemini-test-model")

        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("invalid resume strengths response", context.exception.detail)


class AnalyzeResumeWeaknessesTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_validated_resume_weaknesses(self):
        expected = {
            "weaknesses": [
                "The experience bullet names the work but does not describe its outcome.",
            ],
        }
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(expected)}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            result = await analyze_resume_weaknesses(
                {"experience": [{"title": "Intern", "highlights": ["Built internal tools"]}]},
                "test-api-key",
                "gemini-test-model",
            )

        self.assertEqual(result, expected)
        request = client.post.await_args.kwargs["json"]
        self.assertEqual(
            request["systemInstruction"]["parts"][0]["text"],
            RESUME_WEAKNESSES_SYSTEM_PROMPT,
        )
        self.assertIn('"Built internal tools"', request["contents"][0]["parts"][0]["text"])

    async def test_rejects_unstructured_weaknesses_response(self):
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"weaknesses": "not a list"}'}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            with self.assertRaises(AIAnalysisError) as context:
                await analyze_resume_weaknesses({}, "test-api-key", "gemini-test-model")

        self.assertEqual(context.exception.status_code, 502)
        self.assertIn("invalid resume weaknesses response", context.exception.detail)


class GenerateResumeSummaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_validated_resume_summary(self):
        expected = {
            "summary": (
                "Data analyst with experience automating reports using Python. "
                "Holds a bachelor's degree and has built a sales dashboard."
            ),
        }
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(expected)}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            result = await generate_resume_summary(
                {
                    "skills": {"technical": ["Python"]},
                    "experience": [{"title": "Data analyst"}],
                },
                "test-api-key",
                "gemini-test-model",
            )

        self.assertEqual(result, expected)
        request = client.post.await_args.kwargs["json"]
        self.assertEqual(
            request["systemInstruction"]["parts"][0]["text"],
            RESUME_SUMMARY_SYSTEM_PROMPT,
        )
        self.assertIn('"Python"', request["contents"][0]["parts"][0]["text"])

    async def test_rejects_missing_empty_or_extra_summary_fields(self):
        for response_text in (
            '{"not_summary": "Data analyst."}',
            '{"summary": ""}',
            '{"summary": "Data analyst.", "extra": "unsupported"}',
        ):
            with self.subTest(response_text=response_text):
                response = httpx.Response(
                    200,
                    json={"candidates": [{"content": {"parts": [{"text": response_text}]}}]},
                    request=httpx.Request("POST", "https://example.test"),
                )
                client = AsyncMock()
                client.post.return_value = response
                client_context = AsyncMock()
                client_context.__aenter__.return_value = client
                client_context.__aexit__.return_value = None

                with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
                    with self.assertRaises(AIAnalysisError) as context:
                        await generate_resume_summary({}, "test-api-key", "gemini-test-model")

                self.assertEqual(context.exception.status_code, 502)
                self.assertIn("invalid resume summary response", context.exception.detail)


class GenerateImprovementSuggestionsTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_validated_actionable_suggestions(self):
        expected = {
            "suggestions": [{
                "section": "Experience",
                "priority": "medium",
                "suggestion": "Add a measurable outcome to the reporting automation bullet if you can verify one.",
                "reason": "The experience describes an action but does not state its result.",
            }],
        }
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(expected)}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            result = await generate_improvement_suggestions(
                {"experience": [{"highlights": ["Automated weekly reports"]}]},
                "test-api-key",
                "gemini-test-model",
            )

        self.assertEqual(result, expected)
        request = client.post.await_args.kwargs["json"]
        self.assertEqual(
            request["systemInstruction"]["parts"][0]["text"],
            IMPROVEMENT_SUGGESTIONS_SYSTEM_PROMPT,
        )
        self.assertIn('"Automated weekly reports"', request["contents"][0]["parts"][0]["text"])

    async def test_accepts_empty_suggestion_list(self):
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": '{"suggestions": []}'}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        client_context = AsyncMock()
        client_context.__aenter__.return_value = client
        client_context.__aexit__.return_value = None

        with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
            result = await generate_improvement_suggestions({}, "test-api-key", "gemini-test-model")

        self.assertEqual(result, {"suggestions": []})

    async def test_rejects_invalid_priority_missing_fields_and_more_than_ten_suggestions(self):
        invalid_responses = (
            {"suggestions": [{
                "section": "Experience",
                "priority": "urgent",
                "suggestion": "Clarify this.",
                "reason": "It is unclear.",
            }]},
            {"suggestions": [{"priority": "high", "suggestion": "Clarify this."}]},
            {"suggestions": [
                {
                    "section": "Experience",
                    "priority": "low",
                    "suggestion": f"Suggestion {index}",
                    "reason": "Evidence is unclear.",
                }
                for index in range(11)
            ]},
        )
        for invalid in invalid_responses:
            with self.subTest(invalid=invalid):
                response = httpx.Response(
                    200,
                    json={"candidates": [{"content": {"parts": [{"text": json.dumps(invalid)}]}}]},
                    request=httpx.Request("POST", "https://example.test"),
                )
                client = AsyncMock()
                client.post.return_value = response
                client_context = AsyncMock()
                client_context.__aenter__.return_value = client
                client_context.__aexit__.return_value = None

                with patch("app.services.ai_analysis_service.httpx.AsyncClient", return_value=client_context):
                    with self.assertRaises(AIAnalysisError) as context:
                        await generate_improvement_suggestions({}, "test-api-key", "gemini-test-model")

                self.assertEqual(context.exception.status_code, 502)
                self.assertIn("invalid improvement suggestions", context.exception.detail)


if __name__ == "__main__":
    unittest.main()
