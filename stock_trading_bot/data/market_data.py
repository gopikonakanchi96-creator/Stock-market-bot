from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pandas as pd

from stock_trading_bot.config import StrategyConfig
from stock_trading_bot.models import TechnicalIndicators

logger = logging.getLogger(__name__)


def calculate_rsi(close: pd.Series, window: int = 14) -> float:
    if len(close) < window + 1:
        return 50.0
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(window=window).mean()
    loss = (-delta.clip(upper=0)).rolling(window=window).mean()
    rs = gain / loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    latest = rsi.iloc[-1]
    if pd.isna(latest):
        return 50.0
    return float(latest)


def build_indicators(symbol: str, bars: pd.DataFrame, config: StrategyConfig) -> TechnicalIndicators | None:
    required = {"close", "volume"}
    if bars.empty or not required.issubset(bars.columns):
        return None
    min_rows = max(config.slow_ma_window, config.volume_average_window, config.rsi_window) + 1
    if len(bars) < min_rows:
        return None

    bars = bars.sort_index()
    close = bars["close"].astype(float)
    volume = bars["volume"].astype(float)
    current_price = float(close.iloc[-1])
    previous_close = float(close.iloc[-2])
    sma_fast = float(close.rolling(config.fast_ma_window).mean().iloc[-1])
    sma_slow = float(close.rolling(config.slow_ma_window).mean().iloc[-1])
    avg_volume = float(volume.rolling(config.volume_average_window).mean().iloc[-2])
    rsi = calculate_rsi(close, config.rsi_window)

    trend = "positive" if current_price > previous_close and sma_fast > sma_slow else "negative"
    if abs(sma_fast - sma_slow) / max(current_price, 1) < 0.001:
        trend = "neutral"

    return TechnicalIndicators(
        symbol=symbol,
        current_price=current_price,
        previous_close=previous_close,
        daily_change_pct=(current_price - previous_close) / previous_close if previous_close else 0.0,
        volume=int(volume.iloc[-1]),
        average_volume=avg_volume,
        sma_fast=sma_fast,
        sma_slow=sma_slow,
        rsi=rsi,
        trend=trend,
    )


class AlpacaMarketData:
    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    def fetch_daily_bars(self, symbol: str, limit: int = 120) -> pd.DataFrame:
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockBarsRequest
            from alpaca.data.timeframe import TimeFrame
            import os
        except ImportError as exc:
            raise RuntimeError("alpaca-py is required for Alpaca market data") from exc

        client = StockHistoricalDataClient(os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_SECRET_KEY"))
        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=datetime.now(timezone.utc) - timedelta(days=limit * 2),
            end=datetime.now(timezone.utc),
            limit=limit,
        )
        frame = client.get_stock_bars(request).df
        if frame.empty:
            return frame
        if isinstance(frame.index, pd.MultiIndex):
            frame = frame.xs(symbol)
        return frame.rename(columns=str.lower)

    def get_indicators(self, symbol: str) -> TechnicalIndicators | None:
        try:
            return build_indicators(symbol, self.fetch_daily_bars(symbol), self.config)
        except Exception:
            logger.exception("Failed to fetch market data for %s", symbol)
            return None


class MockMarketData:
    def __init__(self, config: StrategyConfig) -> None:
        self.config = config

    def get_indicators(self, symbol: str) -> TechnicalIndicators | None:
        base = 100 + (sum(ord(ch) for ch in symbol) % 80)
        closes = [base + i * 0.4 for i in range(40)]
        volumes = [900_000 + i * 5_000 for i in range(39)] + [1_600_000]
        bars = pd.DataFrame({"close": closes, "volume": volumes})
        return build_indicators(symbol, bars, self.config)

