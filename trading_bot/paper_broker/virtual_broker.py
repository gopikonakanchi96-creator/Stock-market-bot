from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from trading_bot.app.domain import AccountBalance, Instrument, OrderRequest, OrderResult, OrderSide, Position
from trading_bot.brokers.base import BrokerClient
from trading_bot.strategy.profit_lock import DynamicProfitLock


@dataclass
class PaperTrade:
    timestamp: datetime
    symbol: str
    side: OrderSide
    quantity: int
    price: float
    commission: float
    slippage: float
    realized_pl: float = 0.0


@dataclass
class VirtualBroker(BrokerClient):
    name: str = "virtual_paper_broker"
    starting_balances: dict[str, float] = field(default_factory=lambda: {"USD": 100_000.0, "INR": 1_000_000.0})
    commission_per_order: float = 1.0
    slippage_bps: float = 5.0
    cash: dict[str, float] = field(init=False)
    positions: dict[str, Position] = field(default_factory=dict)
    closed_positions: list[Position] = field(default_factory=list)
    trade_history: list[PaperTrade] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cash = dict(self.starting_balances)

    def balances(self) -> list[AccountBalance]:
        balances = []
        for currency, cash in self.cash.items():
            unrealized = sum(position.unrealized_pl for position in self.positions.values() if position.instrument.currency == currency)
            balances.append(AccountBalance(currency=currency, cash=cash, unrealized_pl=unrealized))
        return balances

    def open_positions(self) -> dict[str, Position]:
        return self.positions

    def submit_order(self, request: OrderRequest) -> OrderResult:
        if request.side == OrderSide.BUY:
            return self.buy(request.instrument, request.quantity, request.estimated_price, request.reason)
        return self.sell(request.instrument, request.quantity, request.estimated_price, request.reason)

    def buy(self, instrument: Instrument, quantity: int, price: float, reason: str = "") -> OrderResult:
        if quantity <= 0 or price <= 0:
            return OrderResult("", False, "rejected", "Invalid quantity or price")
        fill_price = price * (1 + self.slippage_bps / 10_000)
        cost = fill_price * quantity + self.commission_per_order
        available_cash = self.cash.get(instrument.currency, 0.0)
        if cost > available_cash:
            return OrderResult("", False, "rejected", "Insufficient virtual cash")
        self.cash[instrument.currency] = available_cash - cost
        lock = DynamicProfitLock(fill_price)
        self.positions[instrument.symbol] = Position(
            instrument=instrument,
            quantity=quantity,
            entry_price=fill_price,
            current_price=fill_price,
            highest_price=fill_price,
            stop_loss=fill_price * 0.90,
            profit_lock=float(lock.current_lock),
        )
        self.trade_history.append(
            PaperTrade(datetime.now(timezone.utc), instrument.symbol, OrderSide.BUY, quantity, fill_price, self.commission_per_order, fill_price - price)
        )
        return OrderResult(f"paper-{len(self.trade_history)}", True, "filled", reason or "Virtual buy filled", fill_price)

    def sell(self, instrument: Instrument, quantity: int, price: float, reason: str = "") -> OrderResult:
        position = self.positions.get(instrument.symbol)
        if position is None:
            return OrderResult("", False, "rejected", "No open virtual position")
        quantity = min(quantity, position.quantity)
        fill_price = price * (1 - self.slippage_bps / 10_000)
        proceeds = fill_price * quantity - self.commission_per_order
        self.cash[instrument.currency] = self.cash.get(instrument.currency, 0.0) + proceeds
        realized_pl = (fill_price - position.entry_price) * quantity - self.commission_per_order
        position.quantity -= quantity
        if position.quantity <= 0:
            self.closed_positions.append(position)
            self.positions.pop(instrument.symbol, None)
        self.trade_history.append(
            PaperTrade(datetime.now(timezone.utc), instrument.symbol, OrderSide.SELL, quantity, fill_price, self.commission_per_order, price - fill_price, realized_pl)
        )
        return OrderResult(f"paper-{len(self.trade_history)}", True, "filled", reason or "Virtual sell filled", fill_price)

    def update_market_price(self, symbol: str, price: float) -> None:
        position = self.positions.get(symbol)
        if position is None:
            return
        lock = DynamicProfitLock(position.entry_price, position.highest_price, position.profit_lock)
        position.current_price = price
        position.highest_price = max(position.highest_price, price)
        position.profit_lock = lock.update(price)
        position.stop_loss = max(position.stop_loss, position.profit_lock)

