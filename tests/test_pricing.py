from app.usage.pricing import FREE_TIER_DAILY_TOKENS, MODEL_PRICING, ModelPricing, compute_cost


def test_compute_cost_known_model() -> None:
    fake_pricing = ModelPricing(input_per_million=2.0, output_per_million=4.0)

    original = MODEL_PRICING["gpt-5.2"]
    MODEL_PRICING["gpt-5.2"] = fake_pricing
    try:
        cost = compute_cost("gpt-5.2", 1_000_000, 500_000)
    finally:
        MODEL_PRICING["gpt-5.2"] = original

    assert cost == 4.0


def test_compute_cost_unknown_model_returns_none() -> None:
    assert compute_cost("some-unpriced-model", 1000, 1000) is None


def test_compute_cost_matches_dated_snapshot_name() -> None:
    fake_pricing = ModelPricing(input_per_million=2.0, output_per_million=4.0)

    original = MODEL_PRICING["gpt-5.2"]
    MODEL_PRICING["gpt-5.2"] = fake_pricing
    try:
        cost = compute_cost("gpt-5.2-2025-12-11", 1_000_000, 500_000)
    finally:
        MODEL_PRICING["gpt-5.2"] = original

    assert cost == 4.0


def test_compute_cost_free_tier_fully_covers_usage() -> None:
    fake_pricing = ModelPricing(input_per_million=2.0, output_per_million=4.0)

    original_pricing = MODEL_PRICING["gpt-5.2"]
    original_free_tier = FREE_TIER_DAILY_TOKENS["gpt-5.2"]
    MODEL_PRICING["gpt-5.2"] = fake_pricing
    FREE_TIER_DAILY_TOKENS["gpt-5.2"] = 1000
    try:
        cost = compute_cost(
            "gpt-5.2-2025-12-11", 600, 400, apply_free_tier=True, days=1
        )
    finally:
        MODEL_PRICING["gpt-5.2"] = original_pricing
        FREE_TIER_DAILY_TOKENS["gpt-5.2"] = original_free_tier

    assert cost == 0.0


def test_compute_cost_free_tier_deducts_proportionally() -> None:
    fake_pricing = ModelPricing(input_per_million=2.0, output_per_million=4.0)

    original_pricing = MODEL_PRICING["gpt-5.2"]
    original_free_tier = FREE_TIER_DAILY_TOKENS["gpt-5.2"]
    MODEL_PRICING["gpt-5.2"] = fake_pricing
    FREE_TIER_DAILY_TOKENS["gpt-5.2"] = 1000
    try:
        # total=2000, free=1000 -> billable ratio 0.5
        # billable_input=600, billable_output=400
        cost = compute_cost(
            "gpt-5.2-2025-12-11", 1200, 800, apply_free_tier=True, days=1
        )
    finally:
        MODEL_PRICING["gpt-5.2"] = original_pricing
        FREE_TIER_DAILY_TOKENS["gpt-5.2"] = original_free_tier

    assert cost == (600 * 2.0 + 400 * 4.0) / 1_000_000


def test_compute_cost_free_tier_scales_with_days() -> None:
    fake_pricing = ModelPricing(input_per_million=2.0, output_per_million=4.0)

    original_pricing = MODEL_PRICING["gpt-5.2"]
    original_free_tier = FREE_TIER_DAILY_TOKENS["gpt-5.2"]
    MODEL_PRICING["gpt-5.2"] = fake_pricing
    FREE_TIER_DAILY_TOKENS["gpt-5.2"] = 1000
    try:
        # free allowance = 1000 * 3 days = 3000, total usage = 2000 -> fully free
        cost = compute_cost(
            "gpt-5.2-2025-12-11", 1200, 800, apply_free_tier=True, days=3
        )
    finally:
        MODEL_PRICING["gpt-5.2"] = original_pricing
        FREE_TIER_DAILY_TOKENS["gpt-5.2"] = original_free_tier

    assert cost == 0.0


def test_compute_cost_free_tier_ignored_for_other_models() -> None:
    cost_with_flag = compute_cost(
        "gpt-image-2-2026-04-21", 1_000_000, 500_000, apply_free_tier=True
    )
    cost_without_flag = compute_cost("gpt-image-2-2026-04-21", 1_000_000, 500_000)

    assert cost_with_flag == cost_without_flag
