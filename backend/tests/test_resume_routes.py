import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.deps import get_current_user
from app.routes import resume_routes


class FakeResumeCollection:
    def __init__(self, resume, matched_count=1):
        self.resume = resume
        self.matched_count = matched_count
        self.update_call = None

    async def find_one(self, query):
        if self.resume and query["_id"] == self.resume["_id"] and query["user_id"] == self.resume["user_id"]:
            return self.resume
        return None

    async def update_one(self, query, update):
        self.update_call = (query, update)
        return type("UpdateResult", (), {"matched_count": self.matched_count})()


class FakeDatabase:
    def __init__(self, resumes):
        self.resumes = resumes
        self.ai_usage_events = SimpleNamespace(insert_one=AsyncMock())


def assert_saved_analysis(test_case, response, collection, resume_id, analysis_type, result):
    payload = response.json()
    test_case.assertEqual(payload["id"], str(resume_id))
    test_case.assertEqual(payload["analysis"]["type"], analysis_type)
    test_case.assertEqual(payload["analysis"]["result"], result)

    update_query, update = collection.update_call
    saved_result = update["$set"][f"ai_results.{analysis_type}"]
    test_case.assertEqual(update_query["_id"], resume_id)
    test_case.assertEqual(saved_result["result"], result)
    test_case.assertIsNotNone(saved_result["generated_at"])
    test_case.assertEqual(
        payload["analysis"]["generated_at"],
        saved_result["generated_at"].isoformat(),
    )


class UpdateParsedResumeTests(unittest.TestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.resume_id = ObjectId()
        self.resume_doc = {
            "_id": self.resume_id,
            "user_id": self.user_id,
            "file_url": "https://example.com/original.pdf",
            "filename": "original.pdf",
            "parsed": {"name": "Before edit"},
        }
        self.collection = FakeResumeCollection(self.resume_doc)
        self.app = FastAPI()
        self.app.include_router(resume_routes.router)
        self.app.dependency_overrides[get_current_user] = lambda: {"_id": self.user_id}
        self.client = TestClient(self.app)
        self.db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(self.collection))
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.client.close)

    @staticmethod
    def parsed_payload():
        return {
            "name": "Edited Name",
            "contact": {
                "email": "edited@example.com",
                "phone": None,
                "linkedin": None,
                "github": None,
            },
            "summary": None,
            "education": [{"degree": "BSc", "institution": "Example University", "year": "2024"}],
            "experience": [],
            "total_experience_years": 0,
            "projects": [],
            "certifications": ["Cloud Fundamentals"],
            "skills": {"technical": ["Python"], "soft": []},
        }

    def test_updates_only_parsed_fields_for_owned_resume(self):
        response = self.client.put(
            f"/api/resumes/{self.resume_id}/parsed",
            json=self.parsed_payload(),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["parsed"]["education"][0]["year"], "2024")
        self.assertEqual(
            self.collection.update_call,
            (
                {"_id": self.resume_id, "user_id": self.user_id},
                {"$set": {"parsed": self.parsed_payload(), "ai_results": {}}},
            ),
        )
        self.assertEqual(self.resume_doc["file_url"], "https://example.com/original.pdf")
        self.assertEqual(self.resume_doc["filename"], "original.pdf")

    def test_rejects_fields_outside_parsed_resume_schema(self):
        payload = self.parsed_payload()
        payload["file_url"] = "https://attacker.example/"

        response = self.client.put(f"/api/resumes/{self.resume_id}/parsed", json=payload)

        self.assertEqual(response.status_code, 422)
        self.assertIsNone(self.collection.update_call)

    def test_cannot_update_another_users_resume(self):
        self.resume_doc["user_id"] = ObjectId()

        response = self.client.put(
            f"/api/resumes/{self.resume_id}/parsed",
            json=self.parsed_payload(),
        )

        self.assertEqual(response.status_code, 404)
        self.assertIsNone(self.collection.update_call)

    def test_requires_authentication(self):
        self.app.dependency_overrides.pop(get_current_user)

        response = self.client.put(
            f"/api/resumes/{self.resume_id}/parsed",
            json=self.parsed_payload(),
        )

        self.assertEqual(response.status_code, 401)
        self.assertIsNone(self.collection.update_call)

    def test_reports_resume_deleted_between_lookup_and_update(self):
        self.collection.matched_count = 0

        response = self.client.put(
            f"/api/resumes/{self.resume_id}/parsed",
            json=self.parsed_payload(),
        )

        self.assertEqual(response.status_code, 404)


class AnalyzeSkillsRouteTests(unittest.TestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.resume_id = ObjectId()
        self.resume_doc = {
            "_id": self.resume_id,
            "user_id": self.user_id,
            "parsed": {"skills": {"technical": ["Python"]}},
        }
        self.collection = FakeResumeCollection(self.resume_doc)
        self.app = FastAPI()
        self.app.include_router(resume_routes.router)
        self.app.dependency_overrides[get_current_user] = lambda: {"_id": self.user_id}
        self.client = TestClient(self.app)
        self.db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(self.collection))
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.client.close)

    def test_returns_skill_analysis_for_owned_resume(self):
        analysis = {
            "identified_skills": ["Python"],
            "strengths": ["Demonstrates Python in project work."],
            "gaps": ["Role-specific gaps cannot be determined without a target role."],
        }
        with (
            patch.object(
                resume_routes,
                "get_settings",
                return_value=SimpleNamespace(ai_api_key="configured", ai_model_name="gemini-test"),
            ),
            patch.object(
                resume_routes,
                "analyze_resume_skills",
                new_callable=AsyncMock,
                return_value=analysis,
            ) as analyze,
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/skill-analysis")

        self.assertEqual(response.status_code, 200)
        assert_saved_analysis(self, response, self.collection, self.resume_id, "skills", analysis)
        analyze.assert_awaited_once_with(
            self.resume_doc["parsed"],
            "configured",
            "gemini-test",
        )

    def test_requires_a_parsed_resume(self):
        self.resume_doc["parsed"] = None

        with patch.object(resume_routes, "analyze_resume_skills", new_callable=AsyncMock) as analyze:
            response = self.client.post(f"/api/resumes/{self.resume_id}/skill-analysis")

        self.assertEqual(response.status_code, 409)
        analyze.assert_not_awaited()

    def test_returns_configuration_errors_without_hiding_them(self):
        with (
            patch.object(
                resume_routes,
                "get_settings",
                return_value=SimpleNamespace(ai_api_key="", ai_model_name="gemini-test"),
            ),
            patch.object(
                resume_routes,
                "analyze_resume_skills",
                new_callable=AsyncMock,
                side_effect=resume_routes.AIAnalysisError("AI analysis is not configured.", 503),
            ),
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/skill-analysis")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "AI analysis is not configured.")


class AnalyzeExperienceRouteTests(unittest.TestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.resume_id = ObjectId()
        self.resume_doc = {
            "_id": self.resume_id,
            "user_id": self.user_id,
            "parsed": {"experience": [{"title": "Data Intern"}]},
        }
        self.collection = FakeResumeCollection(self.resume_doc)
        self.app = FastAPI()
        self.app.include_router(resume_routes.router)
        self.app.dependency_overrides[get_current_user] = lambda: {"_id": self.user_id}
        self.client = TestClient(self.app)
        self.db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(self.collection))
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.client.close)

    def test_returns_experience_analysis_for_owned_resume(self):
        analysis = {
            "assessment": "The resume gives clear responsibilities.",
            "relevant_strengths": ["Automated a reporting workflow."],
            "gaps": ["Add measured outcomes where available."],
        }
        with (
            patch.object(
                resume_routes,
                "get_settings",
                return_value=SimpleNamespace(ai_api_key="configured", ai_model_name="gemini-test"),
            ),
            patch.object(
                resume_routes,
                "analyze_resume_experience",
                new_callable=AsyncMock,
                return_value=analysis,
            ) as analyze,
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/experience-analysis")

        self.assertEqual(response.status_code, 200)
        assert_saved_analysis(self, response, self.collection, self.resume_id, "experience", analysis)
        analyze.assert_awaited_once_with(
            self.resume_doc["parsed"],
            "configured",
            "gemini-test",
        )

    def test_requires_a_parsed_resume(self):
        self.resume_doc["parsed"] = None

        with patch.object(resume_routes, "analyze_resume_experience", new_callable=AsyncMock) as analyze:
            response = self.client.post(f"/api/resumes/{self.resume_id}/experience-analysis")

        self.assertEqual(response.status_code, 409)
        analyze.assert_not_awaited()

    def test_cannot_analyze_another_users_resume(self):
        self.resume_doc["user_id"] = ObjectId()

        with patch.object(resume_routes, "analyze_resume_experience", new_callable=AsyncMock) as analyze:
            response = self.client.post(f"/api/resumes/{self.resume_id}/experience-analysis")

        self.assertEqual(response.status_code, 404)
        analyze.assert_not_awaited()


class AnalyzeEducationRouteTests(unittest.TestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.resume_id = ObjectId()
        self.resume_doc = {
            "_id": self.resume_id,
            "user_id": self.user_id,
            "parsed": {"education": [{"degree": "BSc", "institution": "Example University"}]},
        }
        self.collection = FakeResumeCollection(self.resume_doc)
        self.app = FastAPI()
        self.app.include_router(resume_routes.router)
        self.app.dependency_overrides[get_current_user] = lambda: {"_id": self.user_id}
        self.client = TestClient(self.app)
        self.db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(self.collection))
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.client.close)

    def test_returns_education_analysis_for_owned_resume(self):
        analysis = {
            "assessment": "The qualification and institution are clearly named.",
            "relevant_details": ["The resume lists a BSc from Example University."],
        }
        with (
            patch.object(
                resume_routes,
                "get_settings",
                return_value=SimpleNamespace(ai_api_key="configured", ai_model_name="gemini-test"),
            ),
            patch.object(
                resume_routes,
                "analyze_resume_education",
                new_callable=AsyncMock,
                return_value=analysis,
            ) as analyze,
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/education-analysis")

        self.assertEqual(response.status_code, 200)
        assert_saved_analysis(self, response, self.collection, self.resume_id, "education", analysis)
        analyze.assert_awaited_once_with(
            self.resume_doc["parsed"],
            "configured",
            "gemini-test",
        )

    def test_requires_a_parsed_resume(self):
        self.resume_doc["parsed"] = None

        with patch.object(resume_routes, "analyze_resume_education", new_callable=AsyncMock) as analyze:
            response = self.client.post(f"/api/resumes/{self.resume_id}/education-analysis")

        self.assertEqual(response.status_code, 409)
        analyze.assert_not_awaited()

    def test_cannot_analyze_another_users_resume(self):
        self.resume_doc["user_id"] = ObjectId()

        with patch.object(resume_routes, "analyze_resume_education", new_callable=AsyncMock) as analyze:
            response = self.client.post(f"/api/resumes/{self.resume_id}/education-analysis")

        self.assertEqual(response.status_code, 404)
        analyze.assert_not_awaited()


class AnalyzeProjectsRouteTests(unittest.TestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.resume_id = ObjectId()
        self.resume_doc = {
            "_id": self.resume_id,
            "user_id": self.user_id,
            "parsed": {
                "projects": [{
                    "name": "Inventory tracker",
                    "technologies": ["React", "MongoDB"],
                }],
            },
        }
        self.collection = FakeResumeCollection(self.resume_doc)
        self.app = FastAPI()
        self.app.include_router(resume_routes.router)
        self.app.dependency_overrides[get_current_user] = lambda: {"_id": self.user_id}
        self.client = TestClient(self.app)
        self.db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(self.collection))
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.client.close)

    def test_returns_project_analysis_for_owned_resume(self):
        analysis = {
            "assessment": "The project explains its purpose and implementation.",
            "project_highlights": ["Built with React and MongoDB."],
        }
        with (
            patch.object(
                resume_routes,
                "get_settings",
                return_value=SimpleNamespace(ai_api_key="configured", ai_model_name="gemini-test"),
            ),
            patch.object(
                resume_routes,
                "analyze_resume_projects",
                new_callable=AsyncMock,
                return_value=analysis,
            ) as analyze,
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/project-analysis")

        self.assertEqual(response.status_code, 200)
        assert_saved_analysis(self, response, self.collection, self.resume_id, "projects", analysis)
        analyze.assert_awaited_once_with(
            self.resume_doc["parsed"],
            "configured",
            "gemini-test",
        )

    def test_requires_a_parsed_resume(self):
        self.resume_doc["parsed"] = None

        with patch.object(resume_routes, "analyze_resume_projects", new_callable=AsyncMock) as analyze:
            response = self.client.post(f"/api/resumes/{self.resume_id}/project-analysis")

        self.assertEqual(response.status_code, 409)
        analyze.assert_not_awaited()

    def test_cannot_analyze_another_users_resume(self):
        self.resume_doc["user_id"] = ObjectId()

        with patch.object(resume_routes, "analyze_resume_projects", new_callable=AsyncMock) as analyze:
            response = self.client.post(f"/api/resumes/{self.resume_id}/project-analysis")

        self.assertEqual(response.status_code, 404)
        analyze.assert_not_awaited()


class AnalyzeStrengthsRouteTests(unittest.TestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.resume_id = ObjectId()
        self.resume_doc = {
            "_id": self.resume_id,
            "user_id": self.user_id,
            "parsed": {"skills": {"technical": ["Python"]}},
        }
        self.collection = FakeResumeCollection(self.resume_doc)
        self.app = FastAPI()
        self.app.include_router(resume_routes.router)
        self.app.dependency_overrides[get_current_user] = lambda: {"_id": self.user_id}
        self.client = TestClient(self.app)
        self.db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(self.collection))
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.client.close)

    def test_returns_strengths_for_owned_resume(self):
        analysis = {"strengths": ["Applied Python in project work."]}
        with (
            patch.object(
                resume_routes,
                "get_settings",
                return_value=SimpleNamespace(ai_api_key="configured", ai_model_name="gemini-test"),
            ),
            patch.object(
                resume_routes,
                "analyze_resume_strengths",
                new_callable=AsyncMock,
                return_value=analysis,
            ) as analyze,
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/strengths-analysis")

        self.assertEqual(response.status_code, 200)
        assert_saved_analysis(self, response, self.collection, self.resume_id, "strengths", analysis)
        analyze.assert_awaited_once_with(
            self.resume_doc["parsed"],
            "configured",
            "gemini-test",
        )

    def test_requires_a_parsed_resume(self):
        self.resume_doc["parsed"] = None

        with patch.object(resume_routes, "analyze_resume_strengths", new_callable=AsyncMock) as analyze:
            response = self.client.post(f"/api/resumes/{self.resume_id}/strengths-analysis")

        self.assertEqual(response.status_code, 409)
        analyze.assert_not_awaited()

    def test_cannot_analyze_another_users_resume(self):
        self.resume_doc["user_id"] = ObjectId()

        with patch.object(resume_routes, "analyze_resume_strengths", new_callable=AsyncMock) as analyze:
            response = self.client.post(f"/api/resumes/{self.resume_id}/strengths-analysis")

        self.assertEqual(response.status_code, 404)
        analyze.assert_not_awaited()


class AnalyzeWeaknessesRouteTests(unittest.TestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.resume_id = ObjectId()
        self.resume_doc = {
            "_id": self.resume_id,
            "user_id": self.user_id,
            "parsed": {"experience": [{"title": "Intern"}]},
        }
        self.collection = FakeResumeCollection(self.resume_doc)
        self.app = FastAPI()
        self.app.include_router(resume_routes.router)
        self.app.dependency_overrides[get_current_user] = lambda: {"_id": self.user_id}
        self.client = TestClient(self.app)
        self.db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(self.collection))
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.client.close)

    def test_returns_weaknesses_for_owned_resume(self):
        analysis = {"weaknesses": ["Add outcomes to the experience details where available."]}
        with (
            patch.object(
                resume_routes,
                "get_settings",
                return_value=SimpleNamespace(ai_api_key="configured", ai_model_name="gemini-test"),
            ),
            patch.object(
                resume_routes,
                "analyze_resume_weaknesses",
                new_callable=AsyncMock,
                return_value=analysis,
            ) as analyze,
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/weaknesses-analysis")

        self.assertEqual(response.status_code, 200)
        assert_saved_analysis(self, response, self.collection, self.resume_id, "weaknesses", analysis)
        analyze.assert_awaited_once_with(
            self.resume_doc["parsed"],
            "configured",
            "gemini-test",
        )

    def test_requires_a_parsed_resume(self):
        self.resume_doc["parsed"] = None

        with patch.object(resume_routes, "analyze_resume_weaknesses", new_callable=AsyncMock) as analyze:
            response = self.client.post(f"/api/resumes/{self.resume_id}/weaknesses-analysis")

        self.assertEqual(response.status_code, 409)
        analyze.assert_not_awaited()

    def test_cannot_analyze_another_users_resume(self):
        self.resume_doc["user_id"] = ObjectId()

        with patch.object(resume_routes, "analyze_resume_weaknesses", new_callable=AsyncMock) as analyze:
            response = self.client.post(f"/api/resumes/{self.resume_id}/weaknesses-analysis")

        self.assertEqual(response.status_code, 404)
        analyze.assert_not_awaited()


class GenerateResumeSummaryRouteTests(unittest.TestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.resume_id = ObjectId()
        self.resume_doc = {
            "_id": self.resume_id,
            "user_id": self.user_id,
            "parsed": {"skills": {"technical": ["Python"]}},
        }
        self.collection = FakeResumeCollection(self.resume_doc)
        self.app = FastAPI()
        self.app.include_router(resume_routes.router)
        self.app.dependency_overrides[get_current_user] = lambda: {"_id": self.user_id}
        self.client = TestClient(self.app)
        self.db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(self.collection))
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.client.close)

    def test_generates_summary_for_owned_resume(self):
        result = {"summary": "Data analyst experienced with Python and reporting automation."}
        with (
            patch.object(
                resume_routes,
                "get_settings",
                return_value=SimpleNamespace(ai_api_key="configured", ai_model_name="gemini-test"),
            ),
            patch.object(
                resume_routes,
                "generate_resume_summary",
                new_callable=AsyncMock,
                return_value=result,
            ) as generate,
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/summary-analysis")

        self.assertEqual(response.status_code, 200)
        assert_saved_analysis(self, response, self.collection, self.resume_id, "summary", result)
        generate.assert_awaited_once_with(
            self.resume_doc["parsed"],
            "configured",
            "gemini-test",
        )

    def test_requires_a_parsed_resume(self):
        self.resume_doc["parsed"] = None

        with patch.object(resume_routes, "generate_resume_summary", new_callable=AsyncMock) as generate:
            response = self.client.post(f"/api/resumes/{self.resume_id}/summary-analysis")

        self.assertEqual(response.status_code, 409)
        generate.assert_not_awaited()

    def test_cannot_generate_summary_for_another_users_resume(self):
        self.resume_doc["user_id"] = ObjectId()

        with patch.object(resume_routes, "generate_resume_summary", new_callable=AsyncMock) as generate:
            response = self.client.post(f"/api/resumes/{self.resume_id}/summary-analysis")

        self.assertEqual(response.status_code, 404)
        generate.assert_not_awaited()


class ImprovementSuggestionsRouteTests(unittest.TestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.resume_id = ObjectId()
        self.resume_doc = {
            "_id": self.resume_id,
            "user_id": self.user_id,
            "parsed": {"experience": [{"title": "Intern"}]},
        }
        self.collection = FakeResumeCollection(self.resume_doc)
        self.app = FastAPI()
        self.app.include_router(resume_routes.router)
        self.app.dependency_overrides[get_current_user] = lambda: {"_id": self.user_id}
        self.client = TestClient(self.app)
        self.db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(self.collection))
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.client.close)

    def test_returns_suggestions_for_owned_resume(self):
        result = {
            "suggestions": [{
                "section": "Experience",
                "priority": "medium",
                "suggestion": "Add an outcome to the experience description if verifiable.",
                "reason": "The current description lists work without explaining its result.",
            }],
        }
        with (
            patch.object(
                resume_routes,
                "get_settings",
                return_value=SimpleNamespace(ai_api_key="configured", ai_model_name="gemini-test"),
            ),
            patch.object(
                resume_routes,
                "generate_improvement_suggestions",
                new_callable=AsyncMock,
                return_value=result,
            ) as generate,
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/improvement-suggestions")

        self.assertEqual(response.status_code, 200)
        assert_saved_analysis(
            self,
            response,
            self.collection,
            self.resume_id,
            "improvement_suggestions",
            result,
        )
        generate.assert_awaited_once_with(
            self.resume_doc["parsed"],
            "configured",
            "gemini-test",
        )

    def test_requires_a_parsed_resume(self):
        self.resume_doc["parsed"] = None

        with patch.object(
            resume_routes,
            "generate_improvement_suggestions",
            new_callable=AsyncMock,
        ) as generate:
            response = self.client.post(f"/api/resumes/{self.resume_id}/improvement-suggestions")

        self.assertEqual(response.status_code, 409)
        generate.assert_not_awaited()

    def test_cannot_generate_suggestions_for_another_users_resume(self):
        self.resume_doc["user_id"] = ObjectId()

        with patch.object(
            resume_routes,
            "generate_improvement_suggestions",
            new_callable=AsyncMock,
        ) as generate:
            response = self.client.post(f"/api/resumes/{self.resume_id}/improvement-suggestions")

        self.assertEqual(response.status_code, 404)
        generate.assert_not_awaited()


class ReparseResumeTests(unittest.TestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.resume_id = ObjectId()
        self.resume_doc = {
            "_id": self.resume_id,
            "user_id": self.user_id,
            "file_url": "https://example.com/resume.pdf",
            "file_type": "pdf",
            "parsed": {"summary": "Before reparse"},
            "ai_results": {"skills": {"result": {"identified_skills": ["Python"]}}},
        }
        self.collection = FakeResumeCollection(self.resume_doc)
        self.app = FastAPI()
        self.app.include_router(resume_routes.router)
        self.app.dependency_overrides[get_current_user] = lambda: {"_id": self.user_id}
        self.client = TestClient(self.app)
        self.db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(self.collection))
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.client.close)

    def test_reparse_clears_saved_ai_results(self):
        class FakeDownloadClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def get(self, url):
                return SimpleNamespace(status_code=200, content=b"%PDF test")

        fake_time = datetime(2026, 10, 4, 12, 0, 0, tzinfo=timezone.utc)
        parsed = {"summary": "After reparse"}
        with (
            patch.object(resume_routes.httpx, "AsyncClient", FakeDownloadClient),
            patch.object(resume_routes, "extract_text", return_value="resume text"),
            patch.object(resume_routes, "parse_resume", return_value=parsed),
            patch.object(resume_routes, "now", return_value=fake_time),
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/parse", json={"parser": "spacy"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(self.resume_id))
        self.assertEqual(response.json()["parsed"], parsed)
        self.assertEqual(response.json()["parser_used"], "spacy")
        self.assertEqual(response.json()["parsed_at"], fake_time.isoformat())
        self.assertEqual(
            self.collection.update_call,
            (
                {"_id": self.resume_id, "user_id": self.user_id},
                {
                    "$set": {
                        "parsed": parsed,
                        "ai_results": {},
                        "parser_used": "spacy",
                        "parsed_at": fake_time,
                    }
                },
            ),
        )

    def test_reparse_with_ai_uses_ai_parser_only(self):
        class FakeDownloadClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def get(self, url):
                return SimpleNamespace(status_code=200, content=b"%PDF test")

        fake_time = datetime(2026, 10, 4, 12, 30, 0, tzinfo=timezone.utc)
        parsed = {"summary": "Parsed by AI"}
        with (
            patch.object(resume_routes.httpx, "AsyncClient", FakeDownloadClient),
            patch.object(resume_routes, "extract_text", return_value="resume text"),
            patch.object(resume_routes, "get_settings", return_value=SimpleNamespace(ai_api_key="configured", ai_model_name="gemini-test", max_ai_parse_chars=40_000)),
            patch.object(resume_routes, "parse_resume_with_ai", new_callable=AsyncMock, return_value=parsed) as parse_ai,
            patch.object(resume_routes, "parse_resume") as parse_spacy,
            patch.object(resume_routes, "now", return_value=fake_time),
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/parse", json={"parser": "ai"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(self.resume_id))
        self.assertEqual(response.json()["parsed"], parsed)
        self.assertEqual(response.json()["parser_used"], "ai")
        self.assertEqual(response.json()["parsed_at"], fake_time.isoformat())
        self.assertEqual(
            self.collection.update_call,
            (
                {"_id": self.resume_id, "user_id": self.user_id},
                {
                    "$set": {
                        "parsed": parsed,
                        "ai_results": {},
                        "parser_used": "ai",
                        "parsed_at": fake_time,
                    }
                },
            ),
        )
        parse_ai.assert_awaited_once_with("resume text", "configured", "gemini-test", 40_000)
        parse_spacy.assert_not_called()

    def test_reparse_download_failure_does_not_clear_ai_results_or_update_db(self):
        class FakeDownloadClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def get(self, url):
                return SimpleNamespace(status_code=500, content=b"")

        with patch.object(resume_routes.httpx, "AsyncClient", FakeDownloadClient):
            response = self.client.post(f"/api/resumes/{self.resume_id}/parse", json={"parser": "spacy"})

        self.assertEqual(response.status_code, 502)
        self.assertIsNone(self.collection.update_call)
        self.assertIn("Python", self.resume_doc["ai_results"]["skills"]["result"]["identified_skills"])

    def test_reparse_parser_error_does_not_clear_ai_results_or_update_db(self):
        class FakeDownloadClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def get(self, url):
                return SimpleNamespace(status_code=200, content=b"%PDF test")

        with (
            patch.object(resume_routes.httpx, "AsyncClient", FakeDownloadClient),
            patch.object(resume_routes, "extract_text", side_effect=resume_routes.ParseError("Corrupted file")),
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/parse", json={"parser": "spacy"})

        self.assertEqual(response.status_code, 422)
        self.assertIsNone(self.collection.update_call)
        self.assertIn("Python", self.resume_doc["ai_results"]["skills"]["result"]["identified_skills"])

    def test_reparse_requires_explicit_parser_choice(self):
        response = self.client.post(f"/api/resumes/{self.resume_id}/parse")

        self.assertEqual(response.status_code, 422)

    def test_reparse_with_ai_provider_error_does_not_switch_to_spacy(self):
        class FakeDownloadClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def get(self, url):
                return SimpleNamespace(status_code=200, content=b"%PDF test")

        with (
            patch.object(resume_routes.httpx, "AsyncClient", FakeDownloadClient),
            patch.object(resume_routes, "extract_text", return_value="resume text"),
            patch.object(resume_routes, "get_settings", return_value=SimpleNamespace(ai_api_key="key", ai_model_name="gemini-test", max_ai_parse_chars=40_000)),
            patch.object(
                resume_routes,
                "parse_resume_with_ai",
                new_callable=AsyncMock,
                side_effect=resume_routes.AIAnalysisError("AI parsing provider timed out. Please try again.", 504),
            ) as parse_ai,
            patch.object(resume_routes, "parse_resume") as parse_spacy,
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/parse", json={"parser": "ai"})

        self.assertEqual(response.status_code, 504)
        self.assertEqual(response.json()["detail"], "AI parsing provider timed out. Please try again.")
        parse_ai.assert_awaited_once()
        parse_spacy.assert_not_called()
        self.assertIsNone(self.collection.update_call)
        self.assertIn("Python", self.resume_doc["ai_results"]["skills"]["result"]["identified_skills"])

    def test_reparse_with_ai_validation_error_does_not_switch_to_spacy(self):
        class FakeDownloadClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def get(self, url):
                return SimpleNamespace(status_code=200, content=b"%PDF test")

        with (
            patch.object(resume_routes.httpx, "AsyncClient", FakeDownloadClient),
            patch.object(resume_routes, "extract_text", return_value="resume text"),
            patch.object(resume_routes, "get_settings", return_value=SimpleNamespace(ai_api_key="key", ai_model_name="gemini-test", max_ai_parse_chars=40_000)),
            patch.object(
                resume_routes,
                "parse_resume_with_ai",
                new_callable=AsyncMock,
                side_effect=resume_routes.AIAnalysisError("AI provider returned an invalid resume parse.", 502),
            ) as parse_ai,
            patch.object(resume_routes, "parse_resume") as parse_spacy,
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/parse", json={"parser": "ai"})

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["detail"], "AI provider returned an invalid resume parse.")
        parse_ai.assert_awaited_once()
        parse_spacy.assert_not_called()
        self.assertIsNone(self.collection.update_call)
        self.assertIn("Python", self.resume_doc["ai_results"]["skills"]["result"]["identified_skills"])

    def test_reparse_with_spacy_parser_error_does_not_switch_to_ai(self):
        class FakeDownloadClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_value, traceback):
                return None

            async def get(self, url):
                return SimpleNamespace(status_code=200, content=b"%PDF test")

        with (
            patch.object(resume_routes.httpx, "AsyncClient", FakeDownloadClient),
            patch.object(resume_routes, "extract_text", return_value="resume text"),
            patch.object(resume_routes, "parse_resume", side_effect=resume_routes.ParseError("Corrupted resume format")) as parse_spacy,
            patch.object(resume_routes, "parse_resume_with_ai", new_callable=AsyncMock) as parse_ai,
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/parse", json={"parser": "spacy"})

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Corrupted resume format")
        parse_spacy.assert_called_once()
        parse_ai.assert_not_called()
        self.assertIsNone(self.collection.update_call)
        self.assertIn("Python", self.resume_doc["ai_results"]["skills"]["result"]["identified_skills"])

    def test_reparse_with_invalid_parser_choice_rejected_without_calling_any_parser(self):
        with (
            patch.object(resume_routes, "parse_resume") as parse_spacy,
            patch.object(resume_routes, "parse_resume_with_ai", new_callable=AsyncMock) as parse_ai,
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/parse", json={"parser": "unknown_engine"})

        self.assertEqual(response.status_code, 422)
        parse_spacy.assert_not_called()
        parse_ai.assert_not_called()
        self.assertIsNone(self.collection.update_call)


class FullResumeAnalysisRouteTests(unittest.TestCase):
    def setUp(self):
        self.user_id = ObjectId()
        self.resume_id = ObjectId()
        self.resume_doc = {
            "_id": self.resume_id,
            "user_id": self.user_id,
            "parsed": {"skills": {"technical": ["Python"]}},
        }
        self.collection = FakeResumeCollection(self.resume_doc)
        self.app = FastAPI()
        self.app.include_router(resume_routes.router)
        self.app.dependency_overrides[get_current_user] = lambda: {"_id": self.user_id}
        self.client = TestClient(self.app)
        self.db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(self.collection))
        self.db_patch.start()
        self.addCleanup(self.db_patch.stop)
        self.addCleanup(self.client.close)

    @staticmethod
    def analysis_result():
        return {
            "skills_analysis": {
                "identified_skills": ["Python"],
                "strengths": ["Uses Python in project work."],
                "gaps": ["Role-specific gaps require a target job."],
            },
            "experience_analysis": {
                "assessment": "Experience is clearly described.",
                "relevant_strengths": ["Automated reporting."],
                "gaps": ["Impact is not quantified."],
            },
            "education_analysis": {
                "assessment": "Education is clearly listed.",
                "relevant_details": ["BSc qualification."],
            },
            "certification_analysis": {
                "assessment": "A certification is clearly listed.",
                "relevant_details": ["Cloud Fundamentals."],
            },
            "project_analysis": {
                "assessment": "Projects demonstrate relevant application.",
                "project_highlights": ["Built a reporting tool."],
            },
            "strengths": ["Evidence of practical experience."],
            "weaknesses": ["Some outcomes lack metrics."],
            "summary": "Candidate with practical Python experience.",
            "improvement_suggestions": [{
                "section": "Experience",
                "priority": "medium",
                "suggestion": "Add verified outcome measures.",
                "reason": "The current bullets focus on tasks.",
            }],
        }

    def test_analyzes_once_and_persists_full_result_for_owned_resume(self):
        analysis = self.analysis_result()
        with (
            patch.object(
                resume_routes,
                "get_settings",
                return_value=SimpleNamespace(ai_api_key="configured", ai_model_name="gemini-test"),
            ),
            patch.object(
                resume_routes,
                "analyze_full_resume",
                new_callable=AsyncMock,
                return_value=analysis,
            ) as analyze,
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/full-analysis")

        self.assertEqual(response.status_code, 200)
        assert_saved_analysis(self, response, self.collection, self.resume_id, "full_resume", analysis)
        analyze.assert_awaited_once_with(
            self.resume_doc["parsed"],
            "configured",
            "gemini-test",
        )

    def test_requires_a_parsed_resume(self):
        self.resume_doc["parsed"] = None

        with patch.object(resume_routes, "analyze_full_resume", new_callable=AsyncMock) as analyze:
            response = self.client.post(f"/api/resumes/{self.resume_id}/full-analysis")

        self.assertEqual(response.status_code, 409)
        analyze.assert_not_awaited()
        self.assertIsNone(self.collection.update_call)

    def test_cannot_analyze_another_users_resume(self):
        self.resume_doc["user_id"] = ObjectId()

        with patch.object(resume_routes, "analyze_full_resume", new_callable=AsyncMock) as analyze:
            response = self.client.post(f"/api/resumes/{self.resume_id}/full-analysis")

        self.assertEqual(response.status_code, 404)
        analyze.assert_not_awaited()
        self.assertIsNone(self.collection.update_call)


class ReparseOwnershipAndAuthTests(unittest.TestCase):
    """
    Ownership checks, authentication, and structured-output shape tests
    for the POST /{resume_id}/parse (reparse) endpoint.
    Structured output must contain all top-level keys that the ParsedResumeUpdate
    schema defines so the frontend can render every section without guards.
    """

    SPACY_PARSED = {
        "name": "Jane Developer",
        "contact": {
            "email": "jane@example.com",
            "phone": "+1-555-0100",
            "linkedin": "linkedin.com/in/jane",
            "github": None,
        },
        "summary": "Experienced Python developer.",
        "education": [{"degree": "BSc Computer Science", "institution": "State University", "year": "2021"}],
        "experience": [
            {
                "title": "Software Engineer",
                "date_range": "Jan 2022 – Present",
                "highlights": ["Led API redesign.", "Reduced latency by 30%."],
                "technologies": ["Python", "FastAPI"],
            }
        ],
        "total_experience_years": 3,
        "projects": [
            {
                "name": "Resume Analyzer",
                "description": ["End-to-end NLP pipeline."],
                "technologies": ["Python", "spaCy"],
            }
        ],
        "certifications": ["AWS Cloud Practitioner"],
        "skills": {"technical": ["Python", "FastAPI", "MongoDB"], "soft": ["Communication"]},
    }

    AI_PARSED = {
        "name": "Jordan AI",
        "contact": {
            "email": "jordan@example.com",
            "phone": None,
            "linkedin": None,
            "github": "github.com/jordan",
        },
        "summary": "ML enthusiast with 5 years of experience.",
        "education": [{"degree": "MSc Data Science", "institution": "Tech University", "year": "2020"}],
        "experience": [],
        "total_experience_years": 5,
        "projects": [],
        "certifications": [],
        "skills": {"technical": ["Python", "TensorFlow"], "soft": ["Problem Solving"]},
    }

    def _make_client(self, user_id, resume_doc):
        collection = FakeResumeCollection(resume_doc)
        app = FastAPI()
        app.include_router(resume_routes.router)
        app.dependency_overrides[get_current_user] = lambda: {"_id": user_id}
        client = TestClient(app)
        db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(collection))
        db_patch.start()
        return client, collection, db_patch

    def _make_download_client(self):
        """Context manager that fakes a successful Cloudinary download."""

        class _FakeDownload:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc_val, tb):
                return None

            async def get(self, url):
                return SimpleNamespace(status_code=200, content=b"%PDF fake content")

        return _FakeDownload

    # ------------------------------------------------------------------ #
    # Ownership checks
    # ------------------------------------------------------------------ #

    def test_cannot_reparse_another_users_resume(self):
        """Reparse of a resume owned by a different user returns 404."""
        owner_id = ObjectId()
        resume_id = ObjectId()
        resume_doc = {
            "_id": resume_id,
            "user_id": owner_id,          # owned by someone else
            "file_url": "https://example.com/resume.pdf",
            "file_type": "pdf",
            "parsed": {"summary": "Owner resume"},
            "ai_results": {},
        }
        requester_id = ObjectId()          # different user
        client, collection, db_patch = self._make_client(requester_id, resume_doc)
        try:
            response = client.post(f"/api/resumes/{resume_id}/parse", json={"parser": "spacy"})
        finally:
            db_patch.stop()
            client.close()

        self.assertEqual(response.status_code, 404)
        self.assertIsNone(collection.update_call)

    def test_reparse_requires_authentication(self):
        """Unauthenticated reparse request returns 401."""
        user_id = ObjectId()
        resume_id = ObjectId()
        resume_doc = {
            "_id": resume_id,
            "user_id": user_id,
            "file_url": "https://example.com/resume.pdf",
            "file_type": "pdf",
            "parsed": {},
            "ai_results": {},
        }
        collection = FakeResumeCollection(resume_doc)
        app = FastAPI()
        app.include_router(resume_routes.router)
        # No dependency override → auth middleware will reject
        client = TestClient(app)
        db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(collection))
        db_patch.start()
        try:
            response = client.post(f"/api/resumes/{resume_id}/parse", json={"parser": "spacy"})
        finally:
            db_patch.stop()
            client.close()

        self.assertEqual(response.status_code, 401)
        self.assertIsNone(collection.update_call)

    def test_reparse_nonexistent_resume_returns_404(self):
        """Reparse of a resume id that doesn't exist returns 404."""
        user_id = ObjectId()
        nonexistent_id = ObjectId()
        # collection has no document
        collection = FakeResumeCollection(None)
        app = FastAPI()
        app.include_router(resume_routes.router)
        app.dependency_overrides[get_current_user] = lambda: {"_id": user_id}
        client = TestClient(app)
        db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(collection))
        db_patch.start()
        try:
            response = client.post(f"/api/resumes/{nonexistent_id}/parse", json={"parser": "spacy"})
        finally:
            db_patch.stop()
            client.close()

        self.assertEqual(response.status_code, 404)

    # ------------------------------------------------------------------ #
    # Structured output shape — spaCy parser
    # ------------------------------------------------------------------ #

    def test_spacy_reparse_response_contains_all_required_structured_output_keys(self):
        """
        A successful spaCy reparse response must include:
          id, parsed, parser_used, parsed_at
        and parsed must contain all top-level ParsedResumeUpdate fields.
        """
        user_id = ObjectId()
        resume_id = ObjectId()
        resume_doc = {
            "_id": resume_id,
            "user_id": user_id,
            "file_url": "https://example.com/resume.pdf",
            "file_type": "pdf",
            "parsed": {"summary": "Old summary"},
            "ai_results": {"skills": {"result": {"identified_skills": ["Java"]}}},
        }
        client, collection, db_patch = self._make_client(user_id, resume_doc)
        fake_time = datetime(2026, 10, 4, 15, 0, 0, tzinfo=timezone.utc)
        try:
            with (
                patch.object(resume_routes.httpx, "AsyncClient", self._make_download_client()),
                patch.object(resume_routes, "extract_text", return_value="Jane Developer\nPython"),
                patch.object(resume_routes, "parse_resume", return_value=self.SPACY_PARSED),
                patch.object(resume_routes, "now", return_value=fake_time),
            ):
                response = client.post(f"/api/resumes/{resume_id}/parse", json={"parser": "spacy"})
        finally:
            db_patch.stop()
            client.close()

        self.assertEqual(response.status_code, 200)
        body = response.json()

        # Top-level response shape
        self.assertIn("id", body)
        self.assertIn("parsed", body)
        self.assertEqual(body["id"], str(resume_id))
        self.assertEqual(body["parser_used"], "spacy")
        self.assertIsNotNone(body["parsed_at"])

        # Every ParsedResumeUpdate field is present in parsed
        parsed = body["parsed"]
        required_keys = {"name", "contact", "summary", "education", "experience",
                         "total_experience_years", "projects", "certifications", "skills"}
        self.assertTrue(
            required_keys.issubset(set(parsed.keys())),
            f"Missing keys: {required_keys - set(parsed.keys())}",
        )

        # Validate nested shapes
        self.assertIsInstance(parsed["contact"], dict)
        contact_keys = {"email", "phone", "linkedin", "github"}
        self.assertTrue(contact_keys.issubset(set(parsed["contact"].keys())))

        self.assertIsInstance(parsed["skills"], dict)
        self.assertIn("technical", parsed["skills"])
        self.assertIn("soft", parsed["skills"])

        self.assertIsInstance(parsed["education"], list)
        self.assertIsInstance(parsed["experience"], list)
        self.assertIsInstance(parsed["projects"], list)
        self.assertIsInstance(parsed["certifications"], list)

        # Content integrity
        self.assertEqual(parsed["name"], "Jane Developer")
        self.assertIn("Python", parsed["skills"]["technical"])
        self.assertEqual(parsed["education"][0]["degree"], "BSc Computer Science")
        self.assertEqual(parsed["experience"][0]["title"], "Software Engineer")
        self.assertEqual(parsed["total_experience_years"], 3)

        # DB write contains the structured output and stale-result clear
        self.assertIsNotNone(collection.update_call)
        db_update = collection.update_call[1]["$set"]
        self.assertEqual(db_update["parsed"], self.SPACY_PARSED)
        self.assertEqual(db_update["ai_results"], {})
        self.assertEqual(db_update["parser_used"], "spacy")
        self.assertEqual(db_update["parsed_at"], fake_time)

    # ------------------------------------------------------------------ #
    # Structured output shape — AI parser
    # ------------------------------------------------------------------ #

    def test_ai_reparse_response_contains_all_required_structured_output_keys(self):
        """
        A successful AI reparse response must include:
          id, parsed, parser_used, parsed_at
        and parsed must have the same schema as the spaCy parser output.
        """
        user_id = ObjectId()
        resume_id = ObjectId()
        resume_doc = {
            "_id": resume_id,
            "user_id": user_id,
            "file_url": "https://example.com/resume.docx",
            "file_type": "docx",
            "parsed": {"name": "Old Name"},
            "ai_results": {
                "experience": {"result": {"assessment": "Old assessment."}},
                "skills": {"result": {"identified_skills": ["Java"]}},
            },
        }
        client, collection, db_patch = self._make_client(user_id, resume_doc)
        fake_time = datetime(2026, 10, 4, 16, 30, 0, tzinfo=timezone.utc)
        try:
            with (
                patch.object(resume_routes.httpx, "AsyncClient", self._make_download_client()),
                patch.object(resume_routes, "extract_text", return_value="Jordan AI\nPython TensorFlow"),
                patch.object(
                    resume_routes,
                    "parse_resume_with_ai",
                    new_callable=AsyncMock,
                    return_value=self.AI_PARSED,
                ) as parse_ai_mock,
                patch.object(resume_routes, "parse_resume") as parse_spacy_mock,
                patch.object(
                    resume_routes,
                    "get_settings",
                    return_value=SimpleNamespace(
                        ai_api_key="test-api-key",
                        ai_model_name="gemini-test",
                        max_ai_parse_chars=40_000,
                    ),
                ),
                patch.object(resume_routes, "now", return_value=fake_time),
            ):
                response = client.post(f"/api/resumes/{resume_id}/parse", json={"parser": "ai"})
        finally:
            db_patch.stop()
            client.close()

        self.assertEqual(response.status_code, 200)
        body = response.json()

        # Top-level response shape
        self.assertIn("id", body)
        self.assertIn("parsed", body)
        self.assertEqual(body["id"], str(resume_id))
        self.assertEqual(body["parser_used"], "ai")
        self.assertIsNotNone(body["parsed_at"])

        # Only AI parser was called
        parse_ai_mock.assert_awaited_once_with(
            "Jordan AI\nPython TensorFlow",
            "test-api-key",
            "gemini-test",
            40_000,
        )
        parse_spacy_mock.assert_not_called()

        # Every ParsedResumeUpdate field is present in parsed
        parsed = body["parsed"]
        required_keys = {"name", "contact", "summary", "education", "experience",
                         "total_experience_years", "projects", "certifications", "skills"}
        self.assertTrue(
            required_keys.issubset(set(parsed.keys())),
            f"Missing keys: {required_keys - set(parsed.keys())}",
        )

        # Content integrity
        self.assertEqual(parsed["name"], "Jordan AI")
        self.assertIn("TensorFlow", parsed["skills"]["technical"])
        self.assertEqual(parsed["total_experience_years"], 5)
        self.assertEqual(parsed["education"][0]["degree"], "MSc Data Science")

        # DB write: stale analysis wiped, parser_used set to "ai"
        self.assertIsNotNone(collection.update_call)
        db_update = collection.update_call[1]["$set"]
        self.assertEqual(db_update["parsed"], self.AI_PARSED)
        self.assertEqual(db_update["ai_results"], {})
        self.assertEqual(db_update["parser_used"], "ai")
        self.assertEqual(db_update["parsed_at"], fake_time)

    # ------------------------------------------------------------------ #
    # Stale-analysis invalidation — ownership combined
    # ------------------------------------------------------------------ #

    def test_stale_analysis_cleared_for_owner_but_not_for_different_user(self):
        """
        When the legitimate owner reparsing succeeds, ai_results is cleared.
        When a different user tries to reparse, the DB is NOT touched and
        the original ai_results are unaffected.
        """
        owner_id = ObjectId()
        attacker_id = ObjectId()
        resume_id = ObjectId()
        existing_ai = {"skills": {"result": {"identified_skills": ["Java"]}}}
        resume_doc = {
            "_id": resume_id,
            "user_id": owner_id,
            "file_url": "https://example.com/resume.pdf",
            "file_type": "pdf",
            "parsed": {"summary": "Original"},
            "ai_results": existing_ai,
        }

        # --- Attacker attempt ---
        collection_attacker = FakeResumeCollection(resume_doc)
        app_attacker = FastAPI()
        app_attacker.include_router(resume_routes.router)
        app_attacker.dependency_overrides[get_current_user] = lambda: {"_id": attacker_id}
        client_attacker = TestClient(app_attacker)
        db_patch_attacker = patch.object(
            resume_routes, "get_db", return_value=FakeDatabase(collection_attacker)
        )
        db_patch_attacker.start()
        try:
            response_attacker = client_attacker.post(
                f"/api/resumes/{resume_id}/parse", json={"parser": "spacy"}
            )
        finally:
            db_patch_attacker.stop()
            client_attacker.close()

        self.assertEqual(response_attacker.status_code, 404)
        self.assertIsNone(collection_attacker.update_call)
        # ai_results untouched
        self.assertEqual(resume_doc["ai_results"], existing_ai)

        # --- Owner attempt succeeds and clears stale ai_results ---
        collection_owner = FakeResumeCollection(resume_doc)
        app_owner = FastAPI()
        app_owner.include_router(resume_routes.router)
        app_owner.dependency_overrides[get_current_user] = lambda: {"_id": owner_id}
        client_owner = TestClient(app_owner)
        db_patch_owner = patch.object(
            resume_routes, "get_db", return_value=FakeDatabase(collection_owner)
        )
        db_patch_owner.start()
        try:
            with (
                patch.object(resume_routes.httpx, "AsyncClient",
                             self._make_download_client()),
                patch.object(resume_routes, "extract_text", return_value="text"),
                patch.object(resume_routes, "parse_resume",
                             return_value={"name": "Updated Name",
                                          "contact": {"email": None, "phone": None, "linkedin": None, "github": None},
                                          "summary": None, "education": [], "experience": [],
                                          "total_experience_years": 0, "projects": [],
                                          "certifications": [],
                                          "skills": {"technical": [], "soft": []}}),
                patch.object(resume_routes, "now",
                             return_value=datetime(2026, 10, 4, 17, 0, tzinfo=timezone.utc)),
            ):
                response_owner = client_owner.post(
                    f"/api/resumes/{resume_id}/parse", json={"parser": "spacy"}
                )
        finally:
            db_patch_owner.stop()
            client_owner.close()

        self.assertEqual(response_owner.status_code, 200)
        self.assertIsNotNone(collection_owner.update_call)
        # Stale ai_results cleared in the DB update
        self.assertEqual(collection_owner.update_call[1]["$set"]["ai_results"], {})

    def test_db_update_rejected_after_ownership_race_condition(self):
        """
        If the document is deleted between _get_owned and update_one
        (matched_count == 0), the route returns 404 even though parsing succeeded.
        """
        user_id = ObjectId()
        resume_id = ObjectId()
        resume_doc = {
            "_id": resume_id,
            "user_id": user_id,
            "file_url": "https://example.com/resume.pdf",
            "file_type": "pdf",
            "parsed": {"summary": "Before"},
            "ai_results": {},
        }
        # matched_count=0 simulates delete-between-find-and-update
        collection = FakeResumeCollection(resume_doc, matched_count=0)
        app = FastAPI()
        app.include_router(resume_routes.router)
        app.dependency_overrides[get_current_user] = lambda: {"_id": user_id}
        client = TestClient(app)
        db_patch = patch.object(resume_routes, "get_db", return_value=FakeDatabase(collection))
        db_patch.start()
        try:
            with (
                patch.object(resume_routes.httpx, "AsyncClient", self._make_download_client()),
                patch.object(resume_routes, "extract_text", return_value="text"),
                patch.object(resume_routes, "parse_resume",
                             return_value={"name": None,
                                          "contact": {"email": None, "phone": None, "linkedin": None, "github": None},
                                          "summary": None, "education": [], "experience": [],
                                          "total_experience_years": 0, "projects": [],
                                          "certifications": [],
                                          "skills": {"technical": [], "soft": []}}),
                patch.object(resume_routes, "now",
                             return_value=datetime(2026, 10, 4, 17, 0, tzinfo=timezone.utc)),
            ):
                response = client.post(f"/api/resumes/{resume_id}/parse", json={"parser": "spacy"})
        finally:
            db_patch.stop()
            client.close()

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
