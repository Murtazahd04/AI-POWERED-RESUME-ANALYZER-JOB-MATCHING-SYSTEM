import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_current_user
from app.routes import admin_routes


class AsyncRows:
    def __init__(self, rows):
        self.rows = rows

    def __aiter__(self):
        async def iterate():
            for row in self.rows:
                yield row
        return iterate()


class FakeCollection:
    def __init__(self, rows):
        self.rows = rows
        self.query = None

    def find(self, query, *_args):
        self.query = query
        return AsyncRows(self.rows)


class AdminAnalyticsRouteTests(unittest.TestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.events = FakeCollection([{
            "user_id": self.user_id, "resume_id": ObjectId(), "model": "gemini-test",
            "operation": "improvement_suggestions", "status": "succeeded", "timestamp": datetime.now(timezone.utc),
            "provider_reported_usage": True, "input_tokens": 100, "output_tokens": 20,
            "estimated_total_cost_usd": 0.01, "recommendation_count": 2,
            "recommendation_cost_attribution": "allocated_from_dedicated_recommendation_request_total",
        }])
        self.database = type("Db", (), {"ai_usage_events": self.events, "resumes": FakeCollection([])})()
        self.app = FastAPI()
        self.app.include_router(admin_routes.router)
        self.client = TestClient(self.app)
        self.db_patch = patch.object(admin_routes, "get_db", return_value=self.database)
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.client.close)

    def test_non_admin_cannot_read_analytics(self):
        self.app.dependency_overrides[get_current_user] = lambda: {"_id": self.user_id, "role": "user"}

        response = self.client.get("/api/admin/analytics")

        self.assertEqual(response.status_code, 403)

    def test_admin_receives_dashboard_metrics_and_date_filter(self):
        self.app.dependency_overrides[get_current_user] = lambda: {"_id": self.user_id, "role": "admin"}

        response = self.client.get("/api/admin/analytics?start_date=2026-10-01&end_date=2026-10-04")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["analyzed_resume_count"], 1)
        self.assertEqual(payload["models"][0]["input_tokens"], 100)
        self.assertEqual(payload["recommendation_costs"][0]["user_id"], str(self.user_id))
        self.assertIn("$gte", self.events.query["timestamp"])
