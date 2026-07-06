from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from stock_trading_bot.models import TradingMode


@dataclass(frozen=True)
class BrokerConfig:
    broker: str
    mode: TradingMode
    allow_live_trading: bool
    alpaca_paper_base_url: str
    alpaca_live_base_url: str


@dataclass(frozen=True)
class RiskConfig:
    risk_per_trade_pct: float
    max_open_positions: int
    max_exposure_per_stock_pct: float
    max_daily_loss_pct: float
    max_trades_per_day: int
    default_trade_notional: float


@dataclass(frozen=True)
class StrategyConfig:
    sentiment_buy_threshold: int
    sentiment_sell_threshold: int
    max_rsi_for_buy: float
    fast_ma_window: int
    slow_ma_window: int
    rsi_window: int
    volume_average_window: int
    min_news_confidence: float


@dataclass(frozen=True)
class AppConfig:
    watchlist: list[str]
    broker: BrokerConfig
    risk: RiskConfig
    strategy: StrategyConfig
    database_path: str
    emergency_stop: bool


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_scalar(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _simple_yaml_load(text: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    current_key: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if indent == 0 and stripped.endswith(":"):
            current_key = stripped[:-1]
            parsed[current_key] = {}
        elif indent == 0 and ":" in stripped:
            key, value = stripped.split(":", 1)
            parsed[key.strip()] = _parse_scalar(value)
            current_key = key.strip()
        elif indent == 2 and stripped.startswith("-") and current_key:
            if not isinstance(parsed.get(current_key), list):
                parsed[current_key] = []
            parsed[current_key].append(_parse_scalar(stripped[1:].strip()))
        elif indent == 2 and ":" in stripped and current_key:
            if not isinstance(parsed.get(current_key), dict):
                parsed[current_key] = {}
            key, value = stripped.split(":", 1)
            parsed[current_key][key.strip()] = _parse_scalar(value)
    return parsed


def load_config(path: str | Path = "stock_trading_bot/config.yaml") -> AppConfig:
    try:
        import yaml
    except ImportError:
        yaml = None

    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
        raw: dict[str, Any] = yaml.safe_load(text) if yaml else _simple_yaml_load(text)
        raw = raw or {}

    broker_raw = raw.get("broker", {})
    mode = TradingMode(str(broker_raw.get("mode", "paper")).lower())
    allow_live = _env_bool("ALLOW_LIVE_TRADING", bool(broker_raw.get("allow_live_trading", False)))

    if mode == TradingMode.LIVE and not allow_live:
        raise RuntimeError(
            "Live trading requested but ALLOW_LIVE_TRADING is not true. "
            "Version 1 is paper-first; keep broker.mode=paper."
        )

    risk_raw = raw.get("risk", {})
    strategy_raw = raw.get("strategy", {})

    return AppConfig(
        watchlist=list(raw.get("watchlist", [])),
        broker=BrokerConfig(
            broker=str(broker_raw.get("name", "alpaca")),
            mode=mode,
            allow_live_trading=allow_live,
            alpaca_paper_base_url=str(broker_raw.get("alpaca_paper_base_url")),
            alpaca_live_base_url=str(broker_raw.get("alpaca_live_base_url")),
        ),
        risk=RiskConfig(
            risk_per_trade_pct=float(risk_raw.get("risk_per_trade_pct", 0.01)),
            max_open_positions=int(risk_raw.get("max_open_positions", 5)),
            max_exposure_per_stock_pct=float(risk_raw.get("max_exposure_per_stock_pct", 0.20)),
            max_daily_loss_pct=float(risk_raw.get("max_daily_loss_pct", 0.03)),
            max_trades_per_day=int(risk_raw.get("max_trades_per_day", 10)),
            default_trade_notional=float(risk_raw.get("default_trade_notional", 1000)),
        ),
        strategy=StrategyConfig(
            sentiment_buy_threshold=int(strategy_raw.get("sentiment_buy_threshold", 25)),
            sentiment_sell_threshold=int(strategy_raw.get("sentiment_sell_threshold", -60)),
            max_rsi_for_buy=float(strategy_raw.get("max_rsi_for_buy", 70)),
            fast_ma_window=int(strategy_raw.get("fast_ma_window", 10)),
            slow_ma_window=int(strategy_raw.get("slow_ma_window", 30)),
            rsi_window=int(strategy_raw.get("rsi_window", 14)),
            volume_average_window=int(strategy_raw.get("volume_average_window", 20)),
            min_news_confidence=float(strategy_raw.get("min_news_confidence", 0.40)),
        ),
        database_path=str(raw.get("database_path", "stock_trading_bot/trading_bot.sqlite3")),
        emergency_stop=_env_bool("EMERGENCY_STOP", bool(raw.get("emergency_stop", False))),
    )
