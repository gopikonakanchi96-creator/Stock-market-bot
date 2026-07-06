from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os

import pandas as pd
import requests

from trading_bot.config.env import load_env_file
from trading_bot.market_data.providers import MarketDataProvider, MarketDataRequest


def _interval_to_provider(timeframe: str) -> tuple[str, str, str, str]:
    mapping = {
        "1m": ("1", "1", "1min", "1min"),
        "5m": ("5", "5", "5min", "5min"),
        "15m": ("15", "15", "15min", "15min"),
        "1h": ("60", "60", "60min", "1h"),
        "1D": ("D", "day", "Daily", "1day"),
    }
    return mapping.get(timeframe, mapping["1D"])


def _ensure_frame(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    if "timestamp" in frame.columns:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
        frame = frame.set_index("timestamp")
    return frame[["open", "high", "low", "close", "volume"]].sort_index()


class FinnhubMarketDataProvider(MarketDataProvider):
    name = "Finnhub"

    def __init__(self) -> None:
        load_env_file()
        self.api_key = os.getenv("FINNHUB_API_KEY")

    def historical_candles(self, request: MarketDataRequest) -> pd.DataFrame:
        if not self.api_key:
            raise RuntimeError("FINNHUB_API_KEY is missing")
        finnhub_resolution, _, _, _ = _interval_to_provider(request.timeframe)
        end = int(datetime.now(timezone.utc).timestamp())
        start = int((datetime.now(timezone.utc) - timedelta(days=max(request.limit * 3, 30))).timestamp())
        response = requests.get(
            "https://finnhub.io/api/v1/stock/candle",
            params={
                "symbol": request.symbol,
                "resolution": finnhub_resolution,
                "from": start,
                "to": end,
                "token": self.api_key,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("s") != "ok":
            raise RuntimeError(f"Finnhub returned status {data.get('s')}")
        rows = [
            {
                "timestamp": datetime.fromtimestamp(ts, timezone.utc),
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
            }
            for ts, open_, high, low, close, volume in zip(data["t"], data["o"], data["h"], data["l"], data["c"], data["v"], strict=False)
        ]
        return _ensure_frame(rows).tail(request.limit)


class PolygonMarketDataProvider(MarketDataProvider):
    name = "Polygon"

    def __init__(self) -> None:
        load_env_file()
        self.api_key = os.getenv("POLYGON_API_KEY")

    def historical_candles(self, request: MarketDataRequest) -> pd.DataFrame:
        if not self.api_key:
            raise RuntimeError("POLYGON_API_KEY is missing")
        _, polygon_multiplier, _, _ = _interval_to_provider(request.timeframe)
        timespan = "day" if request.timeframe == "1D" else "minute"
        multiplier = "1" if request.timeframe == "1D" else polygon_multiplier
        end = datetime.now(timezone.utc).date().isoformat()
        start = (datetime.now(timezone.utc) - timedelta(days=max(request.limit * 3, 30))).date().isoformat()
        response = requests.get(
            f"https://api.polygon.io/v2/aggs/ticker/{request.symbol}/range/{multiplier}/{timespan}/{start}/{end}",
            params={"adjusted": "true", "sort": "asc", "limit": request.limit, "apiKey": self.api_key},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") not in {"OK", "DELAYED"}:
            raise RuntimeError(f"Polygon returned status {data.get('status')}")
        rows = [
            {
                "timestamp": datetime.fromtimestamp(item["t"] / 1000, timezone.utc),
                "open": item["o"],
                "high": item["h"],
                "low": item["l"],
                "close": item["c"],
                "volume": item["v"],
            }
            for item in data.get("results", [])
        ]
        return _ensure_frame(rows).tail(request.limit)


class AlphaVantageMarketDataProvider(MarketDataProvider):
    name = "Alpha Vantage"

    def __init__(self) -> None:
        load_env_file()
        self.api_key = os.getenv("ALPHA_VANTAGE_API_KEY")

    def historical_candles(self, request: MarketDataRequest) -> pd.DataFrame:
        if not self.api_key:
            raise RuntimeError("ALPHA_VANTAGE_API_KEY is missing")
        _, _, alpha_interval, _ = _interval_to_provider(request.timeframe)
        params = {"symbol": request.symbol, "apikey": self.api_key, "outputsize": "compact"}
        if request.timeframe == "1D":
            params["function"] = "TIME_SERIES_DAILY_ADJUSTED"
            series_key = "Time Series (Daily)"
        else:
            params["function"] = "TIME_SERIES_INTRADAY"
            params["interval"] = alpha_interval
            series_key = f"Time Series ({alpha_interval})"
        response = requests.get("https://www.alphavantage.co/query", params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        if "Note" in data or "Information" in data:
            raise RuntimeError(data.get("Note") or data.get("Information"))
        series = data.get(series_key)
        if not series:
            raise RuntimeError("Alpha Vantage response missing time series")
        rows = [
            {
                "timestamp": pd.Timestamp(timestamp, tz="UTC"),
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "volume": float(values.get("6. volume") or values.get("5. volume")),
            }
            for timestamp, values in series.items()
        ]
        return _ensure_frame(rows).tail(request.limit)


class TwelveDataMarketDataProvider(MarketDataProvider):
    name = "Twelve Data"

    def __init__(self) -> None:
        load_env_file()
        self.api_key = os.getenv("TWELVE_DATA_API_KEY")

    def historical_candles(self, request: MarketDataRequest) -> pd.DataFrame:
        if not self.api_key:
            raise RuntimeError("TWELVE_DATA_API_KEY is missing")
        _, _, _, twelve_interval = _interval_to_provider(request.timeframe)
        response = requests.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol": request.symbol,
                "interval": twelve_interval,
                "outputsize": request.limit,
                "apikey": self.api_key,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("status") == "error":
            raise RuntimeError(data.get("message", "Twelve Data error"))
        rows = [
            {
                "timestamp": pd.Timestamp(item["datetime"], tz="UTC"),
                "open": float(item["open"]),
                "high": float(item["high"]),
                "low": float(item["low"]),
                "close": float(item["close"]),
                "volume": float(item.get("volume") or 0),
            }
            for item in data.get("values", [])
        ]
        return _ensure_frame(rows).tail(request.limit)

