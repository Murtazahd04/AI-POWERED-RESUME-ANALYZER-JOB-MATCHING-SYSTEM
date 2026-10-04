import unittest

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_current_user
from app.routes import admin_routes


class AdminAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(admin_routes.router)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def test_rejects_non_admin_users(self):
        self.app.dependency_overrides[get_current_user] = lambda: {
            "_id": ObjectId(), "email": "user@example.com", "role": "user",
        }

        response = self.client.get("/api/admin/access")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["detail"], "Admin access is required.")

    def test_allows_admin_users_without_exposing_password_hash(self):
        self.app.dependency_overrides[get_current_user] = lambda: {
            "_id": ObjectId(),
            "email": "admin@gmail.com",
            "role": "admin",
            "password_hash": "private",
        }

        response = self.client.get("/api/admin/access")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "admin")
        self.assertNotIn("password_hash", response.json())
