from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass(frozen=True)
class TechnicalIndicators:
    symbol: str
    current_price: float
    previous_close: float
    daily_change_pct: float
    volume: int
    average_volume: float
    sma_fast: float
    sma_slow: float
    rsi: float
    trend: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def volume_above_average(self) -> bool:
        return self.average_volume > 0 and self.volume > self.average_volume


@dataclass(frozen=True)
class NewsSentiment:
    symbol: str
    label: str
    score: int
    confidence: float
    headlines: list[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class SignalDecision:
    symbol: str
    action: str
    should_trade: bool
    reason: str
    news_score: int | None
    indicators: TechnicalIndicators | None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    symbol: str
    quantity: int
    entry_price: float
    current_price: float
    highest_price: float
    stop_lock_price: float
    opened_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def market_value(self) -> float:
        return self.quantity * self.current_price

    @property
    def unrealized_pl_pct(self) -> float:
        if self.entry_price <= 0:
            return 0.0
        return (self.current_price - self.entry_price) / self.entry_price


@dataclass(frozen=True)
class OrderRecord:
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    reason: str
    news_score: int | None
    indicators: TechnicalIndicators | None
    stop_lock_price: float | None
    pnl: float | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

