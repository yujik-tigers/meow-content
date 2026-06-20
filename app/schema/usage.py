from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class UsageAggregate:
    period: str
    model: str
    request_count: int
    input_tokens_sum: int
    output_tokens_sum: int


@dataclass(frozen=True, kw_only=True)
class UsageCostSummary:
    period: str
    model: str
    request_count: int
    input_tokens_sum: int
    output_tokens_sum: int
    cost: float | None
