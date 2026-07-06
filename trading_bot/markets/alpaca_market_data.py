from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os

import pandas as pd

from trading_bot.config.env import load_env_file


class AlpacaMarketDataProvider:
    def __init__(self) -> None:
        load_env_file()
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        self._client = None
        if self.api_key and self.secret_key:
            try:
                from alpaca.data.historical import StockHistoricalDataClient

                self._client = StockHistoricalDataClient(self.api_key, self.secret_key)
            except ImportError:
                self._client = None

    @property
    def available(self) -> bool:
        return self._client is not None

    def historical_daily_bars(self, symbol: str, limit: int = 120) -> pd.DataFrame:
        if self._client is None:
            raise RuntimeError("Alpaca market data client is unavailable. Install alpaca-py and set paper API keys.")

        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        from alpaca.data.enums import DataFeed

        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Day,
            start=datetime.now(timezone.utc) - timedelta(days=limit * 3),
            end=datetime.now(timezone.utc),
            limit=limit,
            feed=DataFeed.IEX,
        )
        frame = self._client.get_stock_bars(request).df
        if frame.empty:
            return pd.DataFrame()
        if isinstance(frame.index, pd.MultiIndex):
            frame = frame.xs(symbol)
        return frame.rename(columns=str.lower)
