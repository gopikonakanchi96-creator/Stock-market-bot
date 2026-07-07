from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class OptionCandidate:
    underlying: str
    contract_type: str
    strike: float | None
    expiration: date | None
    bid: float | None
    ask: float | None
    last_price: float | None
    volume: int | None
    open_interest: int | None
    implied_volatility: float | None
    delta: float | None = None
    theta: float | None = None
    gamma: float | None = None
    vega: float | None = None


@dataclass(frozen=True)
class OptionsDashboardSummary:
    enabled: bool
    analysis_only: bool
    watchlist: list[str]
    total_candidates: int
    opportunities: list[OptionCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

