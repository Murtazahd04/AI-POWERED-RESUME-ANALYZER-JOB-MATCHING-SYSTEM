import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError

from app.routes import auth_routes
from app.security import hash_password, verify_password


class FakeUsers:
    def __init__(self, user, other_users=None):
        self.user = user
        self.other_users = other_users or []
        self.update_call = None

    async def find_one(self, query):
        if "email" in query:
            for user in [self.user, *self.other_users]:
                if user["email"] == query["email"] and (
                    "_id" not in query
                    or query["_id"].get("$ne") != user["_id"]
                ):
                    return user
            return None
        return self.user if query == {"_id": self.user["_id"]} else None

    async def find_one_and_update(self, query, update, return_document):
        self.update_call = (query, update)
        if query != {"_id": self.user["_id"]}:
            return None
        self.user.update(update["$set"])
        return self.user

    async def update_one(self, query, update):
        self.update_call = (query, update)
        if query != {"_id": self.user["_id"]}:
            return type("UpdateResult", (), {"matched_count": 0})()
        self.user.update(update["$set"])
        return type("UpdateResult", (), {"matched_count": 1})()


class AuthRouteTests(unittest.TestCase):
    def setUp(self):
        self.user = {
            "_id": ObjectId(), "name": "Admin", "email": "admin@gmail.com", "role": "admin",
            "password_hash": hash_password("AdminPass123"), "created_at": datetime.now(timezone.utc),
        }
        self.app = FastAPI()
        self.app.include_router(auth_routes.router)
        self.app.dependency_overrides[auth_routes.get_current_user] = lambda: self.user
        self.client = TestClient(self.app)
        self.users = FakeUsers(self.user)
        self.db_patch = patch.object(
            auth_routes,
            "get_db",
            return_value=type("Db", (), {"users": self.users})(),
        )
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.app.dependency_overrides.clear)
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

    def test_profile_update_changes_only_allowed_fields_and_redacts_password(self):
        response = self.client.patch(
            "/api/auth/me",
            json={"name": "  Updated Admin  ", "email": "ADMIN@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "Updated Admin")
        self.assertEqual(response.json()["email"], "admin@example.com")
        self.assertEqual(response.json()["role"], "admin")
        self.assertNotIn("password_hash", response.json())
        self.assertEqual(
            self.users.update_call[1],
            {"$set": {"name": "Updated Admin", "email": "admin@example.com"}},
        )

    def test_profile_update_rejects_privileged_or_unknown_fields(self):
        response = self.client.patch(
            "/api/auth/me",
            json={"name": "Updated Admin", "role": "user"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIsNone(self.users.update_call)

    def test_profile_update_requires_a_non_null_field(self):
        response = self.client.patch("/api/auth/me", json={})

        self.assertEqual(response.status_code, 422)
        self.assertIsNone(self.users.update_call)

    def test_profile_update_rejects_duplicate_email(self):
        another_user = {
            "_id": ObjectId(),
            "email": "taken@example.com",
            "name": "Another user",
        }
        self.users.other_users.append(another_user)

        response = self.client.patch(
            "/api/auth/me",
            json={"email": "taken@example.com"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertIsNone(self.users.update_call)

    def test_profile_update_reports_email_uniqueness_race(self):
        with patch.object(
            self.users,
            "find_one_and_update",
            new=AsyncMock(side_effect=DuplicateKeyError("duplicate email")),
        ):
            response = self.client.patch(
                "/api/auth/me",
                json={"email": "new@example.com"},
            )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.json()["detail"],
            "An account with this email already exists.",
        )

    def test_profile_update_requires_authentication(self):
        self.app.dependency_overrides.pop(auth_routes.get_current_user)

        response = self.client.patch("/api/auth/me", json={"name": "Updated Admin"})

        self.assertEqual(response.status_code, 401)
        self.assertIsNone(self.users.update_call)

    def test_password_change_requires_correct_current_password(self):
        response = self.client.post(
            "/api/auth/me/password",
            json={"current_password": "WrongPass123", "new_password": "NewPass456"},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.users.update_call, None)

    def test_password_change_saves_only_new_hash_and_returns_no_password_data(self):
        response = self.client.post(
            "/api/auth/me/password",
            json={"current_password": "AdminPass123", "new_password": "NewPass456"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Password updated."})
        self.assertTrue(verify_password("NewPass456", self.user["password_hash"]))
        self.assertEqual(set(self.users.update_call[1]["$set"]), {"password_hash"})

    def test_password_change_rejects_weak_new_password(self):
        response = self.client.post(
            "/api/auth/me/password",
            json={"current_password": "AdminPass123", "new_password": "allletters"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIsNone(self.users.update_call)

    def test_password_change_requires_authentication(self):
        self.app.dependency_overrides.pop(auth_routes.get_current_user)

        response = self.client.post(
            "/api/auth/me/password",
            json={"current_password": "AdminPass123", "new_password": "NewPass456"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertIsNone(self.users.update_call)
