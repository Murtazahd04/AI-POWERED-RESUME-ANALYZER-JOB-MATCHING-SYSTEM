import unittest
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

        parsed = {"summary": "After reparse"}
        with (
            patch.object(resume_routes.httpx, "AsyncClient", FakeDownloadClient),
            patch.object(resume_routes, "extract_text", return_value="resume text"),
            patch.object(resume_routes, "parse_resume", return_value=parsed),
        ):
            response = self.client.post(f"/api/resumes/{self.resume_id}/parse")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["parsed"], parsed)
        self.assertEqual(
            self.collection.update_call,
            (
                {"_id": self.resume_id, "user_id": self.user_id},
                {"$set": {"parsed": parsed, "ai_results": {}}},
            ),
        )


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


if __name__ == "__main__":
    unittest.main()
