import unittest

from app.services.usage_analytics_service import dashboard_metrics, section_usage, user_recommendation_costs


class UsageAnalyticsTests(unittest.TestCase):
    def test_dashboard_metrics_combines_model_and_resume_totals(self):
        metrics = dashboard_metrics([
            {
                "resume_id": "resume-1", "model": "model-a", "operation": "skills", "status": "succeeded",
                "provider_reported_usage": True, "input_tokens": 100, "output_tokens": 20,
                "estimated_total_cost_usd": 0.02,
            },
            {
                "resume_id": "resume-1", "model": "model-a", "operation": "full_resume", "status": "succeeded",
                "provider_reported_usage": True, "input_tokens": 400, "output_tokens": 80,
                "estimated_total_cost_usd": 0.08,
            },
        ])

        self.assertEqual(metrics["summary"]["analyzed_resume_count"], 1)
        self.assertEqual(metrics["summary"]["successful_analysis_request_count"], 2)
        self.assertEqual(metrics["summary"]["input_tokens"], 500)
        self.assertEqual(metrics["models"][0]["estimated_total_cost_usd"], 0.1)

    def test_section_usage_keeps_full_resume_usage_combined(self):
        summary = section_usage([
            {
                "operation": "skills", "provider_reported_usage": True,
                "input_tokens": 100, "output_tokens": 20, "estimated_total_cost_usd": 0.01,
            },
            {
                "operation": "full_resume", "provider_reported_usage": True,
                "input_tokens": 800, "output_tokens": 300, "estimated_total_cost_usd": 0.2,
            },
        ])

        self.assertEqual(summary[0]["usage_attribution"], "provider_reported_combined_request_no_section_allocation")
        self.assertEqual(summary[0]["input_tokens"], 800)
        self.assertEqual(summary[1]["usage_attribution"], "provider_reported_section_request")
        self.assertEqual(summary[1]["output_tokens"], 20)

    def test_recommendation_cost_is_labeled_as_request_cost_allocation(self):
        user = "user-1"
        summary = user_recommendation_costs([
            {
                "user_id": user, "operation": "improvement_suggestions", "status": "succeeded",
                "recommendation_count": 4, "estimated_total_cost_usd": 0.12,
            },
            {
                "user_id": user, "operation": "improvement_suggestions", "status": "succeeded",
                "recommendation_count": 2, "estimated_total_cost_usd": 0.06,
            },
        ])

        self.assertEqual(summary[0]["recommendation_count"], 6)
        self.assertEqual(summary[0]["estimated_total_cost_usd"], 0.18)
        self.assertEqual(summary[0]["estimated_cost_per_recommendation_usd"], 0.03)
        self.assertEqual(summary[0]["cost_attribution"], "allocated_from_request_total")

    def test_full_resume_recommendations_are_included_with_combined_request_label(self):
        summary = user_recommendation_costs([{
            "user_id": "user-1", "operation": "full_resume", "status": "succeeded",
            "recommendation_count": 3, "estimated_total_cost_usd": 0.09,
            "recommendation_cost_attribution": "allocated_from_combined_full_resume_request_total",
        }])

        self.assertEqual(summary[0]["recommendation_count"], 3)
        self.assertEqual(summary[0]["estimated_cost_per_recommendation_usd"], 0.03)
        self.assertEqual(summary[0]["cost_attribution"], "allocated_from_combined_full_resume_request_total")
