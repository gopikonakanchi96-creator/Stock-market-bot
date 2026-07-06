from __future__ import annotations

from dataclasses import dataclass, field

from trading_bot.app.domain import Instrument, OrderRequest, OrderResult, OrderSide, Position, SignalAction, StrategyDecision
from trading_bot.brokers.base import BrokerClient
from trading_bot.strategy.profit_lock import DynamicProfitLock


@dataclass
class ExecutionService:
    broker: BrokerClient
    positions: dict[str, Position] = field(default_factory=dict)

    def validate_order(self, request: OrderRequest) -> tuple[bool, str]:
        if request.decision.action not in {SignalAction.BUY, SignalAction.SELL}:
            return False, "Decision is not executable"
        if request.quantity <= 0:
            return False, "Quantity must be positive"
        if request.estimated_price <= 0:
            return False, "Estimated price must be positive"
        return True, "Order validation passed"

    def execute(self, request: OrderRequest) -> OrderResult:
        valid, reason = self.validate_order(request)
        if not valid:
            return OrderResult("", False, "rejected", reason)
        result = self.broker.submit_order(request)
        if result.accepted and request.side == OrderSide.BUY:
            lock = DynamicProfitLock(request.estimated_price)
            self.positions[request.instrument.symbol] = Position(
                instrument=request.instrument,
                quantity=request.quantity,
                entry_price=request.estimated_price,
                current_price=request.estimated_price,
                highest_price=request.estimated_price,
                stop_loss=request.estimated_price * 0.90,
                profit_lock=float(lock.current_lock),
            )
        elif result.accepted and request.side == OrderSide.SELL:
            self.positions.pop(request.instrument.symbol, None)
        return result

    def update_position_price(self, symbol: str, current_price: float) -> Position | None:
        position = self.positions.get(symbol)
        if not position:
            return None
        lock = DynamicProfitLock(position.entry_price, position.highest_price, position.profit_lock)
        position.current_price = current_price
        position.highest_price = max(position.highest_price, current_price)
        position.profit_lock = lock.update(current_price)
        position.stop_loss = max(position.stop_loss, position.profit_lock)
        return position

