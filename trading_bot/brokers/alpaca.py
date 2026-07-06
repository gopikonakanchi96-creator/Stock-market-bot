from __future__ import annotations

import os

from trading_bot.app.domain import AccountBalance, BrokerMode, OrderRequest, OrderResult, OrderSide, Position
from trading_bot.brokers.base import BrokerClient


class AlpacaPaperBroker(BrokerClient):
    name = "alpaca"

    def __init__(self, mode: BrokerMode = BrokerMode.PAPER) -> None:
        if mode != BrokerMode.PAPER:
            raise RuntimeError("Version 1 supports Alpaca paper trading only.")
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret = os.getenv("ALPACA_SECRET_KEY")
        self._client = None
        if self.api_key and self.secret:
            try:
                from alpaca.trading.client import TradingClient

                self._client = TradingClient(self.api_key, self.secret, paper=True)
            except ImportError:
                self._client = None

    def balances(self) -> list[AccountBalance]:
        if self._client is None:
            return [AccountBalance(currency="USD", cash=100_000)]
        account = self._client.get_account()
        return [AccountBalance(currency="USD", cash=float(account.cash))]

    def open_positions(self) -> dict[str, Position]:
        return {}

    def submit_order(self, request: OrderRequest) -> OrderResult:
        if request.instrument.currency != "USD":
            return OrderResult("", False, "rejected", "Alpaca broker only supports USD instruments in V1")
        if request.quantity <= 0:
            return OrderResult("", False, "rejected", "Quantity must be positive")
        if self._client is None:
            return OrderResult("alpaca-mock-paper", True, "paper_filled", "Mock Alpaca paper fill", request.estimated_price)

        from alpaca.trading.enums import OrderSide as AlpacaSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        order = self._client.submit_order(
            MarketOrderRequest(
                symbol=request.instrument.symbol,
                qty=request.quantity,
                side=AlpacaSide.BUY if request.side == OrderSide.BUY else AlpacaSide.SELL,
                time_in_force=TimeInForce.DAY,
            )
        )
        return OrderResult(str(order.id), True, str(order.status), "Submitted to Alpaca paper", request.estimated_price)

