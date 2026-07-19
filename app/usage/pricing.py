from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPricing:
    input_per_million: float
    output_per_million: float


MODEL_PRICING: dict[str, ModelPricing] = {
    "gpt-5.2": ModelPricing(input_per_million=1.75, output_per_million=14.00),
    "gpt-image-2-2026-04-21": ModelPricing(
        input_per_million=8.0, output_per_million=30.0
    ),
    "gemini-3.1-flash-image": ModelPricing(
        input_per_million=0.5, output_per_million=60.0
    ),
    "gemini-3-pro-image": ModelPricing(input_per_million=2.0, output_per_million=120.0),
    "text-embedding-3-small": ModelPricing(input_per_million=0.02, output_per_million=0.0),
}

# Daily free token allowance (input + output combined), keyed the same way as
# MODEL_PRICING (exact match or dated-snapshot prefix match).
FREE_TIER_DAILY_TOKENS: dict[str, int] = {
    "gpt-5.2": 250_000,
}


def _resolve_key(model: str, table: Mapping[str, object]) -> str | None:
    if model in table:
        return model

    # Some providers (e.g. OpenAI) return a dated snapshot name
    # (e.g. "gpt-5.2-2025-12-11") instead of the requested alias ("gpt-5.2").
    matching_keys = [key for key in table if model.startswith(f"{key}-")]
    if not matching_keys:
        return None
    return max(matching_keys, key=len)


def compute_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    *,
    apply_free_tier: bool = False,
    days: int = 1,
) -> float | None:
    pricing_key = _resolve_key(model, MODEL_PRICING)
    if pricing_key is None:
        return None
    pricing = MODEL_PRICING[pricing_key]

    billable_input, billable_output = input_tokens, output_tokens
    if apply_free_tier:
        free_tier_key = _resolve_key(model, FREE_TIER_DAILY_TOKENS)
        if free_tier_key is not None:
            total_tokens = input_tokens + output_tokens
            free_tokens = FREE_TIER_DAILY_TOKENS[free_tier_key] * days
            billable_tokens = max(0, total_tokens - free_tokens)
            if total_tokens > 0:
                ratio = billable_tokens / total_tokens
                billable_input = input_tokens * ratio
                billable_output = output_tokens * ratio

    return (
        billable_input * pricing.input_per_million
        + billable_output * pricing.output_per_million
    ) / 1_000_000
