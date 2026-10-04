import unittest

from app.services.parser_service import parse_resume


class ParseResumeTests(unittest.TestCase):
    def test_singular_certification_heading_does_not_leak_into_experience(self):
        parsed = parse_resume(
            "Murtaza Huzefa Dhanerawala\n"
            "EXPERIENCE\n"
            "AI/ML Research Intern\n"
            "Jan 2024 - Dec 2024\n"
            "Built data tools.\n"
            "CERTIFICATION\n"
            "Azure AI Fundamentals\n"
        )

        self.assertEqual(parsed["certifications"], ["Azure AI Fundamentals"])
        self.assertNotIn("CERTIFICATION", parsed["experience"][0]["highlights"])
        self.assertNotIn("Azure AI Fundamentals", parsed["experience"][0]["highlights"])

    def test_education_merges_degree_institution_and_standalone_year(self):
        parsed = parse_resume(
            "Example Person\n"
            "EDUCATION\n"
            "Bachelor of Technology in Computer Engineering\n"
            "Example Institute\n"
            "2024\n"
        )

        self.assertEqual(
            parsed["education"],
            [{
                "degree": "Bachelor of Technology in Computer Engineering",
                "institution": "Example Institute",
                "year": "2024",
            }],
        )

    def test_projects_parse_when_present_and_are_empty_when_absent(self):
        with_projects = parse_resume(
            "Example Person\n"
            "PROJECTS\n"
            "Resume Analyzer\n"
            "- Built a resume analyzer.\n"
        )
        without_projects = parse_resume("Example Person\nEDUCATION\nBachelor of Science\n")

        self.assertEqual(with_projects["projects"][0]["name"], "Resume Analyzer")
        self.assertEqual(without_projects["projects"], [])

    def test_social_links_are_empty_when_not_present(self):
        parsed = parse_resume("Example Person\nEDUCATION\nBachelor of Science\n")

        self.assertIsNone(parsed["contact"]["linkedin"])
        self.assertIsNone(parsed["contact"]["github"])


if __name__ == "__main__":
    unittest.main()
