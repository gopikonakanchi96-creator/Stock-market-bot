from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class OptionType(str, Enum):
    CALL = "CALL"
    PUT = "PUT"


class OptionSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


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
class OptionContract:
    underlying: str
    contract_type: OptionType
    strike: float
    expiration: date
    premium: float
    currency: str = "USD"
    multiplier: int = 100

    @property
    def symbol(self) -> str:
        expiry = self.expiration.strftime("%Y%m%d")
        return f"{self.underlying}-{expiry}-{self.contract_type.value}-{self.strike:.2f}"


@dataclass(frozen=True)
class OptionOrderRequest:
    contract: OptionContract
    side: OptionSide
    quantity: int
    reason: str


@dataclass(frozen=True)
class OptionOrderResult:
    order_id: str
    accepted: bool
    status: str
    reason: str
    filled_premium: float | None = None


@dataclass
class OptionPosition:
    contract: OptionContract
    quantity: int
    entry_premium: float
    current_premium: float

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_premium * self.contract.multiplier

    @property
    def unrealized_pl(self) -> float:
        return self.quantity * (self.current_premium - self.entry_premium) * self.contract.multiplier


@dataclass(frozen=True)
class OptionsDashboardSummary:
    enabled: bool
    analysis_only: bool
    paper_trading_enabled: bool
    watchlist: list[str]
    total_candidates: int
    opportunities: list[OptionCandidate] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)
