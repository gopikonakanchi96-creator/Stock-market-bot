from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from trading_bot.app.domain import IndicatorSet, Market
from trading_bot.config.settings import StrategySettings
from trading_bot.markets.alpaca_market_data import AlpacaMarketDataProvider


def _rsi(close: pd.Series, window: int) -> float:
    if len(close) <= window:
        return 50.0
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window).mean()
    loss = (-delta.clip(upper=0)).rolling(window).mean()
    rs = gain / loss.replace(0, pd.NA)
    latest = (100 - (100 / (1 + rs))).iloc[-1]
    return 50.0 if pd.isna(latest) else float(latest)


def _atr(frame: pd.DataFrame, window: int) -> float:
    high = frame.get("high", frame["close"]).astype(float)
    low = frame.get("low", frame["close"]).astype(float)
    close = frame["close"].astype(float)
    previous_close = close.shift(1)
    true_range = pd.concat([(high - low), (high - previous_close).abs(), (low - previous_close).abs()], axis=1).max(axis=1)
    latest = true_range.rolling(window).mean().iloc[-1]
    return 0.0 if pd.isna(latest) else float(latest)


def build_indicators(frame: pd.DataFrame, settings: StrategySettings) -> IndicatorSet | None:
    if frame.empty or not {"close", "volume"}.issubset(frame.columns):
        return None
    min_rows = max(settings.slow_ma_window, settings.rsi_window, settings.atr_window) + 2
    if len(frame) < min_rows:
        return None
    frame = frame.sort_index()
    close = frame["close"].astype(float)
    volume = frame["volume"].astype(float)
    sma_fast = close.rolling(settings.fast_ma_window).mean().iloc[-1]
    sma_slow = close.rolling(settings.slow_ma_window).mean().iloc[-1]
    ema_12 = close.ewm(span=12, adjust=False).mean()
    ema_26 = close.ewm(span=26, adjust=False).mean()
    macd_series = ema_12 - ema_26
    macd_signal = macd_series.ewm(span=9, adjust=False).mean()
    typical = frame.get("high", close).astype(float).add(frame.get("low", close).astype(float)).add(close) / 3
    vwap = (typical * volume).cumsum().iloc[-1] / volume.cumsum().iloc[-1]
    volatility = close.pct_change().rolling(20).std().iloc[-1]
    current = float(close.iloc[-1])
    previous = float(close.iloc[-2])
    trend = "positive" if current > previous and sma_fast > sma_slow and macd_series.iloc[-1] > macd_signal.iloc[-1] else "negative"
    return IndicatorSet(
        current_price=current,
        previous_close=previous,
        volume=int(volume.iloc[-1]),
        average_volume=float(volume.rolling(20).mean().iloc[-2]),
        sma_fast=float(sma_fast),
        sma_slow=float(sma_slow),
        rsi=_rsi(close, settings.rsi_window),
        macd=float(macd_series.iloc[-1]),
        macd_signal=float(macd_signal.iloc[-1]),
        vwap=float(vwap),
        atr=_atr(frame, settings.atr_window),
        volatility=0.0 if pd.isna(volatility) else float(volatility),
        trend=trend,
    )


class MarketDataService:
    def __init__(self, settings: StrategySettings, alpaca_provider: AlpacaMarketDataProvider | None = None) -> None:
        self.settings = settings
        self.alpaca_provider = alpaca_provider or AlpacaMarketDataProvider()

    def market_is_open(self, market: Market, now: datetime | None = None) -> bool:
        now = now or datetime.now(ZoneInfo(market.timezone))
        if now.weekday() >= 5:
            return False
        if market.code == "US":
            return now.replace(hour=9, minute=30) <= now <= now.replace(hour=16, minute=0)
        if market.code == "India":
            return now.replace(hour=9, minute=15) <= now <= now.replace(hour=15, minute=30)
        return False

    def market_status(self, market: Market) -> dict[str, str | bool]:
        return {"market": market.code, "open": self.market_is_open(market), "timezone": market.timezone}

    def historical_candles(self, symbol: str, market: Market, limit: int = 80) -> pd.DataFrame:
        if market.code == "US":
            return self.alpaca_provider.historical_daily_bars(symbol, limit=max(limit, 120))
        base = 100 + (sum(ord(ch) for ch in symbol + market.currency) % 70)
        closes = [base + i * 0.35 for i in range(limit)]
        highs = [value * 1.01 for value in closes]
        lows = [value * 0.99 for value in closes]
        volumes = [900_000 + i * 4_000 for i in range(limit - 1)] + [1_600_000]
        return pd.DataFrame({"close": closes, "high": highs, "low": lows, "volume": volumes})

    def indicators(self, symbol: str, market: Market) -> IndicatorSet | None:
        try:
            return build_indicators(self.historical_candles(symbol, market), self.settings)
        except Exception:
            return None

    def data_snapshot(self, symbol: str, market: Market) -> dict[str, object]:
        try:
            frame = self.historical_candles(symbol, market)
            error = None
        except Exception as exc:
            frame = pd.DataFrame()
            error = str(exc)
        indicators = build_indicators(frame, self.settings)
        latest_bar_time = None
        stale_days = None
        is_stale = True
        if not frame.empty:
            latest_bar_time = frame.index[-1]
            latest_ts = pd.Timestamp(latest_bar_time).to_pydatetime()
            if latest_ts.tzinfo is None:
                latest_ts = latest_ts.replace(tzinfo=timezone.utc)
            stale_days = (datetime.now(timezone.utc) - latest_ts.astimezone(timezone.utc)).days
            is_stale = stale_days > 7
        return {
            "symbol": symbol,
            "market": market.code,
            "country": market.country,
            "currency": market.currency,
            "rows": len(frame),
            "latest_bar_time": str(latest_bar_time) if latest_bar_time is not None else None,
            "stale_days": stale_days,
            "is_stale": is_stale,
            "indicators": indicators.__dict__ if indicators else None,
            "data_available": indicators is not None and not is_stale,
            "error": error,
        }
