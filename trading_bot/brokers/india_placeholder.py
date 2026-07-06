from __future__ import annotations

from trading_bot.app.domain import AccountBalance, OrderRequest, OrderResult, Position
from trading_bot.brokers.base import BrokerClient


class IndianBrokerPlaceholder(BrokerClient):
    name = "indian_placeholder"

    def balances(self) -> list[AccountBalance]:
        return [AccountBalance(currency="INR", cash=2_500_000)]

    def open_positions(self) -> dict[str, Position]:
        return {}

    def submit_order(self, request: OrderRequest) -> OrderResult:
        return OrderResult(
            order_id="india-placeholder-paper",
            accepted=True,
            status="paper_simulated",
            reason="Indian broker interface is ready; V1 uses placeholder paper simulation.",
            filled_price=request.estimated_price,
        )

