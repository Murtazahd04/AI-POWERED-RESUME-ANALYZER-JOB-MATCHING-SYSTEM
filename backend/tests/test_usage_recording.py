import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId

from app.routes import resume_routes


class UsageRecordingTests(unittest.IsolatedAsyncioTestCase):
    async def test_records_provider_tokens_costs_and_rate_snapshot(self):
        events = SimpleNamespace(insert_one=AsyncMock())
        database = SimpleNamespace(ai_usage_events=events)
        user = {"_id": ObjectId()}
        settings = SimpleNamespace(
            ai_pricing_version="rate-card-1",
            ai_model_rates={"gemini-test": {
                "input_usd_per_million_tokens": 0.4,
                "output_usd_per_million_tokens": 1.6,
            }},
        )

        with (
            patch.object(resume_routes, "get_provider_usage", return_value={"input_tokens": 1_000_000, "output_tokens": 500_000}),
            patch.object(resume_routes, "get_settings", return_value=settings),
            patch.object(resume_routes, "get_db", return_value=database),
        ):
            await resume_routes._record_ai_usage(user, str(ObjectId()), "skills", "gemini-test", "succeeded")

        event = events.insert_one.await_args.args[0]
        self.assertEqual(event["input_tokens"], 1_000_000)
        self.assertEqual(event["output_tokens"], 500_000)
        self.assertEqual(event["estimated_input_cost_usd"], 0.4)
        self.assertEqual(event["estimated_output_cost_usd"], 0.8)
        self.assertEqual(event["estimated_total_cost_usd"], 1.2)
        self.assertEqual(event["rate_snapshot"]["pricing_version_ref"], "rate-card-1")
        self.assertNotIn("raw_text", event)
        self.assertNotIn("resume_text", event)
