import json
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from app.services.ai_analysis_service import AIAnalysisError
from app.services.ai_parser_service import parse_resume_with_ai, prepare_resume_text_for_ai


VALID_PARSE = {
    "name": "Avery Example",
    "contact": {"email": "avery@example.com", "phone": None, "linkedin": None, "github": None},
    "summary": None,
    "education": [],
    "experience": [],
    "total_experience_years": 0,
    "projects": [],
    "certifications": [],
    "skills": {"technical": ["Python"], "soft": []},
}


class AIParserTests(unittest.IsolatedAsyncioTestCase):
    async def test_returns_existing_validated_resume_schema(self):
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(VALID_PARSE)}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        context = AsyncMock()
        context.__aenter__.return_value = client
        context.__aexit__.return_value = None

        with patch("app.services.ai_parser_service.httpx.AsyncClient", return_value=context):
            parsed = await parse_resume_with_ai("Avery Example\r\n\r\n\r\nSkills: Python\x00", "key", "gemini-test")

        self.assertEqual(parsed, VALID_PARSE)
        request = client.post.await_args
        self.assertEqual(request.kwargs["json"]["generationConfig"]["temperature"], 0)
        sent_text = request.kwargs["json"]["contents"][0]["parts"][0]["text"]
        self.assertEqual(sent_text, "Avery Example\n\nSkills: Python")
        self.assertNotIn("\x00", sent_text)

    async def test_rejects_parse_with_unexpected_or_invented_schema_fields(self):
        invalid = {**VALID_PARSE, "made_up_field": "not allowed"}
        response = httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": json.dumps(invalid)}]}}]},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        context = AsyncMock()
        context.__aenter__.return_value = client
        context.__aexit__.return_value = None

        with patch("app.services.ai_parser_service.httpx.AsyncClient", return_value=context):
            with self.assertRaises(AIAnalysisError) as raised:
                await parse_resume_with_ai("Avery Example", "key", "gemini-test")

        self.assertIn("invalid resume parse", raised.exception.detail)

    async def test_rejects_oversized_text_before_contacting_provider(self):
        with patch("app.services.ai_parser_service.httpx.AsyncClient") as client:
            with self.assertRaises(AIAnalysisError) as raised:
                await parse_resume_with_ai("x" * 11, "key", "gemini-test", max_chars=10)

        self.assertEqual(raised.exception.status_code, 413)
        client.assert_not_called()

    def test_prepared_text_contains_only_normalized_resume_text(self):
        self.assertEqual(prepare_resume_text_for_ai("  Name\r\n\r\n\r\nSkills  ", 100), "Name\n\nSkills")

    async def test_reports_provider_timeout_clearly(self):
        client = AsyncMock()
        client.post.side_effect = httpx.TimeoutException("timed out")
        context = AsyncMock()
        context.__aenter__.return_value = client
        context.__aexit__.return_value = None

        with patch("app.services.ai_parser_service.httpx.AsyncClient", return_value=context):
            with self.assertRaises(AIAnalysisError) as raised:
                await parse_resume_with_ai("Avery Example", "key", "gemini-test")

        self.assertEqual(raised.exception.status_code, 504)
        self.assertIn("timed out", raised.exception.detail)

    async def test_reports_provider_connection_error_clearly(self):
        client = AsyncMock()
        client.post.side_effect = httpx.RequestError("connection refused")
        context = AsyncMock()
        context.__aenter__.return_value = client
        context.__aexit__.return_value = None

        with patch("app.services.ai_parser_service.httpx.AsyncClient", return_value=context):
            with self.assertRaises(AIAnalysisError) as raised:
                await parse_resume_with_ai("Avery Example", "key", "gemini-test")

        self.assertEqual(raised.exception.status_code, 502)
        self.assertIn("Could not reach", raised.exception.detail)

    async def test_reports_provider_rate_limit_clearly(self):
        response = httpx.Response(
            429,
            json={"error": {"message": "Rate limit exceeded"}},
            request=httpx.Request("POST", "https://example.test"),
        )
        client = AsyncMock()
        client.post.return_value = response
        context = AsyncMock()
        context.__aenter__.return_value = client
        context.__aexit__.return_value = None

        with patch("app.services.ai_parser_service.httpx.AsyncClient", return_value=context):
            with self.assertRaises(AIAnalysisError) as raised:
                await parse_resume_with_ai("Avery Example", "key", "gemini-test")

        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("rate-limiting", raised.exception.detail)

    async def test_reports_missing_configuration_clearly(self):
        with self.assertRaises(AIAnalysisError) as raised:
            await parse_resume_with_ai("Avery Example", "", "gemini-test")
        self.assertEqual(raised.exception.status_code, 503)
        self.assertIn("not configured", raised.exception.detail)

        with self.assertRaises(AIAnalysisError) as raised2:
            await parse_resume_with_ai("Avery Example", "key", "")
        self.assertEqual(raised2.exception.status_code, 503)
        self.assertIn("not configured", raised2.exception.detail)
