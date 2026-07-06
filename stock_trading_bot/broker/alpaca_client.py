from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from stock_trading_bot.config import BrokerConfig
from stock_trading_bot.models import OrderSide, Position, TradingMode
from stock_trading_bot.strategy.profit_lock import ProfitLock

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class BrokerOrderResult:
    id: str
    symbol: str
    side: OrderSide
    quantity: int
    submitted_price: float
    status: str


class AlpacaBrokerClient:
    def __init__(self, config: BrokerConfig) -> None:
        if config.mode != TradingMode.PAPER:
            raise RuntimeError("Version 1 supports Alpaca paper trading only.")
        self.config = config
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        if not self.api_key or not self.secret_key:
            raise RuntimeError("Set ALPACA_API_KEY and ALPACA_SECRET_KEY for Alpaca paper trading.")

        try:
            from alpaca.trading.client import TradingClient
        except ImportError as exc:
            raise RuntimeError("Install alpaca-py to use AlpacaBrokerClient.") from exc

        self.client = TradingClient(self.api_key, self.secret_key, paper=True)

    def get_account_equity(self) -> float:
        account = self.client.get_account()
        return float(account.equity)

    def submit_market_order(self, symbol: str, side: OrderSide, quantity: int, estimated_price: float) -> BrokerOrderResult:
        from alpaca.trading.enums import OrderSide as AlpacaSide, TimeInForce
        from alpaca.trading.requests import MarketOrderRequest

        if quantity <= 0:
            raise ValueError("quantity must be positive")
        request = MarketOrderRequest(
            symbol=symbol,
            qty=quantity,
            side=AlpacaSide.BUY if side == OrderSide.BUY else AlpacaSide.SELL,
            time_in_force=TimeInForce.DAY,
        )
        order = self.client.submit_order(request)
        logger.info("Submitted Alpaca paper order %s %s x%d", side.value, symbol, quantity)
        return BrokerOrderResult(
            id=str(order.id),
            symbol=symbol,
            side=side,
            quantity=quantity,
            submitted_price=estimated_price,
            status=str(order.status),
        )

    def get_open_positions(self) -> dict[str, Position]:
        positions: dict[str, Position] = {}
        for raw_position in self.client.get_all_positions():
            symbol = str(raw_position.symbol)
            qty = int(float(raw_position.qty))
            entry = float(raw_position.avg_entry_price)
            current = float(raw_position.current_price)
            lock = ProfitLock(entry_price=entry, highest_price=max(entry, current))
            lock.update(current)
            positions[symbol] = Position(
                symbol=symbol,
                quantity=qty,
                entry_price=entry,
                current_price=current,
                highest_price=float(lock.highest_price),
                stop_lock_price=float(lock.current_lock_price),
            )
        return positions


class MockBrokerClient:
    def __init__(self, starting_equity: float = 100_000.0) -> None:
        self.equity = starting_equity
        self._order_id = 0

    def get_account_equity(self) -> float:
        return self.equity

    def submit_market_order(self, symbol: str, side: OrderSide, quantity: int, estimated_price: float) -> BrokerOrderResult:
        self._order_id += 1
        return BrokerOrderResult(
            id=f"mock-{self._order_id}",
            symbol=symbol,
            side=side,
            quantity=quantity,
            submitted_price=estimated_price,
            status="filled",
        )

    def get_open_positions(self) -> dict[str, Position]:
        return {}
