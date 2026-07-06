from __future__ import annotations

import os

from trading_bot.app.domain import BrokerMode
from trading_bot.brokers.alpaca import AlpacaPaperBroker
from trading_bot.config.env import load_env_file


def check_alpaca_paper_connection() -> dict[str, object]:
    load_env_file()
    api_key = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_SECRET_KEY")
    if not api_key or not secret:
        return {
            "ok": False,
            "broker": "alpaca",
            "mode": "paper",
            "reason": "ALPACA_API_KEY or ALPACA_SECRET_KEY is missing",
        }

    broker = AlpacaPaperBroker(BrokerMode.PAPER)
    if broker._client is None:
        return {
            "ok": False,
            "broker": "alpaca",
            "mode": "paper",
            "reason": "alpaca-py is not installed or the client could not be created",
        }

    account = broker._client.get_account()
    return {
        "ok": True,
        "broker": "alpaca",
        "mode": "paper",
        "account_number": str(getattr(account, "account_number", ""))[-4:],
        "status": str(getattr(account, "status", "")),
        "currency": str(getattr(account, "currency", "USD")),
        "cash": float(getattr(account, "cash", 0)),
        "equity": float(getattr(account, "equity", 0)),
        "buying_power": float(getattr(account, "buying_power", 0)),
        "pattern_day_trader": bool(getattr(account, "pattern_day_trader", False)),
        "trading_blocked": bool(getattr(account, "trading_blocked", False)),
        "transfers_blocked": bool(getattr(account, "transfers_blocked", False)),
        "account_blocked": bool(getattr(account, "account_blocked", False)),
    }

