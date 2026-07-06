from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from trading_bot.app.domain import IndicatorSet, Market
from trading_bot.config.settings import StrategySettings
from trading_bot.market_data.cache import InMemoryTTLCache
from trading_bot.market_data.providers import MarketDataProvider, MarketDataRequest, configured_provider_chain
from trading_bot.markets.market_data import build_indicators


def _sanitize_error(message: str) -> str:
    for marker in ["token=", "apiKey=", "apikey="]:
        if marker in message:
            parts = message.split(marker)
            rebuilt = parts[0]
            for rest in parts[1:]:
                separator_index = rest.find("&")
                if separator_index == -1:
                    rebuilt += marker + "***"
                else:
                    rebuilt += marker + "***" + rest[separator_index:]
            message = rebuilt
    return message


class EnterpriseMarketDataService:
    def __init__(
        self,
        settings: StrategySettings,
        provider_priority: list[str],
        providers: list[MarketDataProvider] | None = None,
        cache: InMemoryTTLCache | None = None,
    ) -> None:
        self.settings = settings
        self.providers = providers or configured_provider_chain(provider_priority)
        self.cache = cache or InMemoryTTLCache()
        self.last_provider_name: str | None = None
        self.last_provider_errors: list[str] = []

    def market_is_open(self, market: Market, now: datetime | None = None) -> bool:
        now = now or datetime.now(ZoneInfo(market.timezone))
        if now.weekday() >= 5:
            return False
        if market.code == "US":
            return now.replace(hour=9, minute=30) <= now <= now.replace(hour=16, minute=0)
        if market.code == "India":
            return now.replace(hour=9, minute=15) <= now <= now.replace(hour=15, minute=30)
        return False

    def exchange_status(self, market: Market) -> dict[str, object]:
        return {
            "market": market.code,
            "country": market.country,
            "timezone": market.timezone,
            "is_open": self.market_is_open(market),
            "holiday": False,
        }

    def historical_candles(self, symbol: str, market: Market, timeframe: str = "1D", limit: int = 120) -> pd.DataFrame:
        cache_key = f"candles:{market.code}:{symbol}:{timeframe}:{limit}"
        cached = self.cache.get(cache_key)
        if cached is not None:
            self.last_provider_name = "cache"
            self.last_provider_errors = []
            return cached.copy()

        request = MarketDataRequest(symbol=symbol, market=market, timeframe=timeframe, limit=limit)
        errors: list[str] = []
        for provider in self.providers:
            try:
                frame = provider.historical_candles(request)
                if not frame.empty and {"close", "volume"}.issubset(frame.columns):
                    self.cache.set(cache_key, frame.copy(), ttl_seconds=60)
                    self.last_provider_name = provider.name
                    self.last_provider_errors = errors
                    return frame
                errors.append(f"{provider.name}: empty/incomplete response")
            except Exception as exc:
                errors.append(_sanitize_error(f"{provider.name}: {exc}"))
                continue
        self.last_provider_name = None
        self.last_provider_errors = errors
        raise RuntimeError("; ".join(errors))

    def live_price(self, symbol: str, market: Market) -> float | None:
        frame = self.historical_candles(symbol, market, timeframe="1m", limit=2)
        if frame.empty:
            return None
        return float(frame["close"].iloc[-1])

    def indicators(self, symbol: str, market: Market, timeframe: str = "1D") -> IndicatorSet | None:
        try:
            return build_indicators(self.historical_candles(symbol, market, timeframe=timeframe), self.settings)
        except Exception:
            return None
