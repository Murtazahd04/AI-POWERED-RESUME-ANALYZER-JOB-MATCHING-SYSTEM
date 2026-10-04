import unittest

from app.services.ai_cost_service import calculate_estimated_costs


class EstimatedCostTests(unittest.TestCase):
    def test_calculates_input_output_and_total_from_rate_snapshot(self):
        result = calculate_estimated_costs(
            1_500_000,
            250_000,
            {"input_usd_per_million_tokens": 0.4, "output_usd_per_million_tokens": 1.6},
            "2026-10-rate-card",
        )

        self.assertEqual(result["estimated_input_cost_usd"], 0.6)
        self.assertEqual(result["estimated_output_cost_usd"], 0.4)
        self.assertEqual(result["estimated_total_cost_usd"], 1.0)
        self.assertEqual(
            result["rate_snapshot"],
            {
                "pricing_version_ref": "2026-10-rate-card",
                "currency": "USD",
                "configured": True,
                "input_usd_per_million_tokens": 0.4,
                "output_usd_per_million_tokens": 1.6,
            },
        )

    def test_preserves_unconfigured_rate_and_does_not_invent_costs(self):
        result = calculate_estimated_costs(100, 50, None, "unconfigured")

        self.assertIsNone(result["estimated_input_cost_usd"])
        self.assertIsNone(result["estimated_output_cost_usd"])
        self.assertIsNone(result["estimated_total_cost_usd"])
        self.assertFalse(result["rate_snapshot"]["configured"])
