from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from trading_bot.app.domain import BrokerMode, Market


@dataclass(frozen=True)
class RiskSettings:
    risk_per_trade: float
    max_open_positions: int
    max_exposure_per_stock: float
    max_exposure_per_sector: float
    max_daily_loss: float
    max_weekly_loss: float
    max_monthly_drawdown: float
    max_trades_per_day: int
    emergency_stop: bool


@dataclass(frozen=True)
class StrategySettings:
    min_news_score: int
    min_ai_confidence: float
    max_rsi_for_buy: float
    min_risk_score: float
    fast_ma_window: int
    slow_ma_window: int
    rsi_window: int
    atr_window: int
    position_sizing: str
    default_trade_amount: float


@dataclass(frozen=True)
class AppSettings:
    app_name: str
    base_currency: str
    paper_trading: bool
    live_trading: bool
    broker_mode: BrokerMode
    markets: dict[str, Market]
    watchlists: dict[str, list[str]]
    risk: RiskSettings
    strategy: StrategySettings
    database_url: str
    redis_url: str
    market_data_provider_priority: list[str]
    paper_starting_balances: dict[str, float]


def _parse_scalar(value: str) -> Any:
    value = value.strip().strip('"').strip("'")
    if value.endswith("%"):
        return float(value[:-1]) / 100
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return float(value) if "." in value else int(value)
    except ValueError:
        return value


def _fallback_yaml(text: str) -> dict[str, Any]:
    lines: list[tuple[int, str]] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if line.strip():
            lines.append((len(line) - len(line.lstrip(" ")), line.strip()))

    def parse_block(index: int, indent: int) -> tuple[Any, int]:
        if index >= len(lines):
            return {}, index
        if lines[index][1].startswith("-"):
            values: list[Any] = []
            while index < len(lines) and lines[index][0] == indent and lines[index][1].startswith("-"):
                values.append(_parse_scalar(lines[index][1][1:].strip()))
                index += 1
            return values, index

        values: dict[str, Any] = {}
        while index < len(lines):
            current_indent, stripped = lines[index]
            if current_indent < indent:
                break
            if current_indent > indent:
                index += 1
                continue
            if stripped.startswith("-"):
                break
            key, value = stripped.split(":", 1)
            key = key.strip()
            if value.strip():
                values[key] = _parse_scalar(value)
                index += 1
            else:
                next_index = index + 1
                if next_index >= len(lines) or lines[next_index][0] <= current_indent:
                    values[key] = {}
                    index = next_index
                else:
                    values[key], index = parse_block(next_index, lines[next_index][0])
        return values, index

    parsed, _ = parse_block(0, 0)
    return parsed


def _load_yaml(path: str | Path) -> dict[str, Any]:
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml

        return yaml.safe_load(text) or {}
    except ImportError:
        return _fallback_yaml(text)


def load_settings(path: str | Path = "config.yaml") -> AppSettings:
    raw = _load_yaml(path)
    live_trading = bool(raw.get("live_trading", False))
    paper_trading = bool(raw.get("paper_trading", True))
    if live_trading and os.getenv("ALLOW_LIVE_TRADING", "false").lower() != "true":
        raise RuntimeError("Live trading requires ALLOW_LIVE_TRADING=true and explicit code review.")
    mode = BrokerMode.LIVE if live_trading else BrokerMode.PAPER

    markets: dict[str, Market] = {}
    for code, item in (raw.get("markets") or {}).items():
        markets[code] = Market(
            code=code,
            country=str(item.get("country", code)),
            currency=str(item.get("currency", "USD")),
            exchanges=list(item.get("exchanges", [])),
            broker=str(item.get("broker", "placeholder")),
            enabled=bool(item.get("enabled", False)),
            timezone=str(item.get("timezone", "UTC")),
        )

    risk_raw = raw.get("risk", {})
    strategy_raw = raw.get("strategy", {})
    return AppSettings(
        app_name=str(raw.get("app_name", "AI Trading Bot")),
        base_currency=str(raw.get("base_currency", "USD")),
        paper_trading=paper_trading,
        live_trading=live_trading,
        broker_mode=mode,
        markets=markets,
        watchlists={k: list(v) for k, v in (raw.get("watchlists") or {}).items()},
        risk=RiskSettings(
            risk_per_trade=float(risk_raw.get("risk_per_trade", 0.02)),
            max_open_positions=int(risk_raw.get("max_open_positions", 10)),
            max_exposure_per_stock=float(risk_raw.get("max_exposure_per_stock", 0.15)),
            max_exposure_per_sector=float(risk_raw.get("max_exposure_per_sector", 0.30)),
            max_daily_loss=float(risk_raw.get("max_daily_loss", 0.03)),
            max_weekly_loss=float(risk_raw.get("max_weekly_loss", 0.06)),
            max_monthly_drawdown=float(risk_raw.get("max_monthly_drawdown", 0.10)),
            max_trades_per_day=int(risk_raw.get("max_trades_per_day", 20)),
            emergency_stop=os.getenv("EMERGENCY_STOP", str(risk_raw.get("emergency_stop", False))).lower() == "true",
        ),
        strategy=StrategySettings(
            min_news_score=int(strategy_raw.get("min_news_score", 25)),
            min_ai_confidence=float(strategy_raw.get("min_ai_confidence", 0.55)),
            max_rsi_for_buy=float(strategy_raw.get("max_rsi_for_buy", 70)),
            min_risk_score=float(strategy_raw.get("min_risk_score", 0.50)),
            fast_ma_window=int(strategy_raw.get("fast_ma_window", 10)),
            slow_ma_window=int(strategy_raw.get("slow_ma_window", 30)),
            rsi_window=int(strategy_raw.get("rsi_window", 14)),
            atr_window=int(strategy_raw.get("atr_window", 14)),
            position_sizing=str(strategy_raw.get("position_sizing", "risk_based")),
            default_trade_amount=float(strategy_raw.get("default_trade_amount", 1000)),
        ),
        database_url=os.getenv("DATABASE_URL", str(raw.get("database_url", "postgresql+psycopg://trader:trader@localhost:5432/trading_bot"))),
        redis_url=os.getenv("REDIS_URL", str(raw.get("redis_url", "redis://localhost:6379/0"))),
        market_data_provider_priority=list((raw.get("market_data") or {}).get("provider_priority", [])),
        paper_starting_balances={
            key: float(value)
            for key, value in ((raw.get("paper_trading_config") or {}).get("starting_balances", {"USD": 100_000, "INR": 1_000_000})).items()
        },
    )
