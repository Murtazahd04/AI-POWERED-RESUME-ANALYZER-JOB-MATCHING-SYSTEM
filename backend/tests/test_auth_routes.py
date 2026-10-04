import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import auth_routes
from app.security import hash_password


class FakeUsers:
    def __init__(self, user):
        self.user = user

    async def find_one(self, query):
        return self.user if query == {"email": self.user["email"]} else None


class AuthRouteTests(unittest.TestCase):
    def setUp(self):
        self.user = {
            "_id": ObjectId(), "name": "Admin", "email": "admin@gmail.com", "role": "admin",
            "password_hash": hash_password("AdminPass123"), "created_at": datetime.now(timezone.utc),
        }
        self.app = FastAPI()
        self.app.include_router(auth_routes.router)
        self.client = TestClient(self.app)
        self.db_patch = patch.object(auth_routes, "get_db", return_value=type("Db", (), {"users": FakeUsers(self.user)})())
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.client.close)

    def test_admin_can_log_in_and_receives_admin_role(self):
        response = self.client.post("/api/auth/login", json={"email": "admin@gmail.com", "password": "AdminPass123"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["role"], "admin")
        self.assertTrue(response.json()["access_token"])
        self.assertNotIn("password_hash", response.json()["user"])

    def test_login_rejects_wrong_password(self):
        response = self.client.post("/api/auth/login", json={"email": "admin@gmail.com", "password": "WrongPass123"})

        self.assertEqual(response.status_code, 401)
