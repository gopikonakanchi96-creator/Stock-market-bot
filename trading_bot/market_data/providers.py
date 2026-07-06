from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from trading_bot.app.domain import Market


@dataclass(frozen=True)
class MarketDataRequest:
    symbol: str
    market: Market
    timeframe: str = "1D"
    limit: int = 120


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    def historical_candles(self, request: MarketDataRequest) -> pd.DataFrame:
        raise NotImplementedError

    def live_price(self, symbol: str, market: Market) -> float | None:
        candles = self.historical_candles(MarketDataRequest(symbol=symbol, market=market, limit=2))
        if candles.empty:
            return None
        return float(candles["close"].iloc[-1])


class NotConfiguredProvider(MarketDataProvider):
    def __init__(self, name: str) -> None:
        self.name = name

    def historical_candles(self, request: MarketDataRequest) -> pd.DataFrame:
        raise RuntimeError(f"{self.name} API key/provider is not configured")


class DeterministicFallbackProvider(MarketDataProvider):
    name = "DeterministicFallback"

    def historical_candles(self, request: MarketDataRequest) -> pd.DataFrame:
        base = 100 + (sum(ord(ch) for ch in request.symbol + request.market.currency) % 80)
        step = 0.22 if request.timeframe != "1D" else 0.35
        closes = [base + idx * step for idx in range(request.limit)]
        index = pd.date_range(end=datetime.now(timezone.utc), periods=request.limit, freq="D")
        return pd.DataFrame(
            {
                "open": [value * 0.998 for value in closes],
                "high": [value * 1.01 for value in closes],
                "low": [value * 0.99 for value in closes],
                "close": closes,
                "volume": [900_000 + idx * 5_000 for idx in range(request.limit - 1)] + [1_700_000],
            },
            index=index,
        )


def configured_provider_chain(priority: list[str]) -> list[MarketDataProvider]:
    from trading_bot.market_data.http_providers import (
        AlphaVantageMarketDataProvider,
        FinnhubMarketDataProvider,
        PolygonMarketDataProvider,
        TwelveDataMarketDataProvider,
    )

    providers: list[MarketDataProvider] = []
    for name in priority:
        normalized = name.strip().lower()
        if normalized == "finnhub":
            providers.append(FinnhubMarketDataProvider())
        elif normalized == "polygon":
            providers.append(PolygonMarketDataProvider())
        elif normalized == "alpha vantage":
            providers.append(AlphaVantageMarketDataProvider())
        elif normalized == "twelve data":
            providers.append(TwelveDataMarketDataProvider())
        else:
            providers.append(NotConfiguredProvider(name))
    providers.append(DeterministicFallbackProvider())
    return providers
