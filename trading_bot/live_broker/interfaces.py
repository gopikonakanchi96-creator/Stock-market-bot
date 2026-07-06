from __future__ import annotations

from abc import ABC, abstractmethod

from trading_bot.app.domain import Instrument, OrderResult


class LiveBroker(ABC):
    name: str

    @abstractmethod
    def buy(self, instrument: Instrument, quantity: int, limit_price: float | None = None) -> OrderResult:
        raise NotImplementedError

    @abstractmethod
    def sell(self, instrument: Instrument, quantity: int, limit_price: float | None = None) -> OrderResult:
        raise NotImplementedError


class InteractiveBrokersAdapter(LiveBroker):
    name = "interactive_brokers"

    def buy(self, instrument: Instrument, quantity: int, limit_price: float | None = None) -> OrderResult:
        return OrderResult("", False, "not_implemented", "Interactive Brokers adapter is not enabled in V1")

    def sell(self, instrument: Instrument, quantity: int, limit_price: float | None = None) -> OrderResult:
        return OrderResult("", False, "not_implemented", "Interactive Brokers adapter is not enabled in V1")


class IndianBrokerAdapter(LiveBroker):
    name = "indian_broker_interface"

    def buy(self, instrument: Instrument, quantity: int, limit_price: float | None = None) -> OrderResult:
        return OrderResult("", False, "not_implemented", "Indian live broker adapter is not enabled in V1")

    def sell(self, instrument: Instrument, quantity: int, limit_price: float | None = None) -> OrderResult:
        return OrderResult("", False, "not_implemented", "Indian live broker adapter is not enabled in V1")

