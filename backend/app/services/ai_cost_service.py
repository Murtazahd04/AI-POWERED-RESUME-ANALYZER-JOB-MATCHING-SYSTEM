"""Cost estimation based on the rate card active when an AI request completes."""
from decimal import Decimal, ROUND_HALF_UP


def _cost(tokens: int | None, rate_per_million: float) -> float | None:
    if not isinstance(tokens, int) or tokens < 0:
        return None
    value = (Decimal(tokens) * Decimal(str(rate_per_million))) / Decimal("1000000")
    return float(value.quantize(Decimal("0.000000000001"), rounding=ROUND_HALF_UP))


def calculate_estimated_costs(
    input_tokens: int | None,
    output_tokens: int | None,
    model_rate: dict[str, float] | None,
    pricing_version_ref: str,
) -> dict:
    """Return costs and a self-contained snapshot of the rate card used."""
    if model_rate is None:
        return {
            "estimated_input_cost_usd": None,
            "estimated_output_cost_usd": None,
            "estimated_total_cost_usd": None,
            "rate_snapshot": {
                "pricing_version_ref": pricing_version_ref,
                "currency": "USD",
                "configured": False,
            },
        }

    input_rate = model_rate["input_usd_per_million_tokens"]
    output_rate = model_rate["output_usd_per_million_tokens"]
    input_cost = _cost(input_tokens, input_rate)
    output_cost = _cost(output_tokens, output_rate)
    total = None if input_cost is None or output_cost is None else round(input_cost + output_cost, 12)
    return {
        "estimated_input_cost_usd": input_cost,
        "estimated_output_cost_usd": output_cost,
        "estimated_total_cost_usd": total,
        "rate_snapshot": {
            "pricing_version_ref": pricing_version_ref,
            "currency": "USD",
            "configured": True,
            "input_usd_per_million_tokens": input_rate,
            "output_usd_per_million_tokens": output_rate,
        },
    }
