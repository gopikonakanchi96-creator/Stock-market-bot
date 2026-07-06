from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    WAIT = "WAIT"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class BrokerMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


@dataclass(frozen=True)
class Market:
    code: str
    country: str
    currency: str
    exchanges: list[str]
    broker: str
    enabled: bool
    timezone: str


@dataclass(frozen=True)
class Instrument:
    symbol: str
    name: str
    market: str
    country: str
    exchange: str
    currency: str
    sector: str = "Unknown"


@dataclass(frozen=True)
class IndicatorSet:
    current_price: float
    previous_close: float
    volume: int
    average_volume: float
    sma_fast: float
    sma_slow: float
    rsi: float
    macd: float
    macd_signal: float
    vwap: float
    atr: float
    volatility: float
    trend: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def volume_confirmed(self) -> bool:
        return self.average_volume > 0 and self.volume > self.average_volume


@dataclass(frozen=True)
class NewsSignal:
    label: str
    score: int
    confidence: float
    freshness_minutes: float
    source_reliability: float
    headlines: list[str]


@dataclass(frozen=True)
class StrategyDecision:
    action: SignalAction
    confidence: float
    explanation: str
    news_score: int
    risk_score: float
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    instrument: Instrument
    quantity: int
    entry_price: float
    current_price: float
    highest_price: float
    stop_loss: float
    profit_lock: float
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pl(self) -> float:
        return (self.current_price - self.entry_price) * self.quantity


@dataclass(frozen=True)
class AccountBalance:
    currency: str
    cash: float
    realized_pl: float = 0.0
    unrealized_pl: float = 0.0


@dataclass(frozen=True)
class OrderRequest:
    instrument: Instrument
    side: OrderSide
    quantity: int
    estimated_price: float
    reason: str
    decision: StrategyDecision


@dataclass(frozen=True)
class OrderResult:
    order_id: str
    accepted: bool
    status: str
    reason: str
    filled_price: float | None = None

