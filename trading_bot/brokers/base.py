from __future__ import annotations

from abc import ABC, abstractmethod

from trading_bot.app.domain import AccountBalance, OrderRequest, OrderResult, Position


class BrokerClient(ABC):
    name: str

    @abstractmethod
    def balances(self) -> list[AccountBalance]:
        raise NotImplementedError

    @abstractmethod
    def open_positions(self) -> dict[str, Position]:
        raise NotImplementedError

    @abstractmethod
    def submit_order(self, request: OrderRequest) -> OrderResult:
        raise NotImplementedError

