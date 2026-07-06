from __future__ import annotations

from trading_bot.app.domain import BrokerMode
from trading_bot.brokers.alpaca import AlpacaPaperBroker
from trading_bot.brokers.base import BrokerClient
from trading_bot.brokers.india_placeholder import IndianBrokerPlaceholder


def broker_for(name: str, mode: BrokerMode) -> BrokerClient:
    if name == "alpaca":
        return AlpacaPaperBroker(mode)
    if name == "indian_placeholder":
        return IndianBrokerPlaceholder()
    raise ValueError(f"No broker configured for {name}")

