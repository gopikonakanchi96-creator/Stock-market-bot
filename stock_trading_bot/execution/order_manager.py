from __future__ import annotations

import logging

from stock_trading_bot.database import TradingDatabase
from stock_trading_bot.models import OrderRecord, OrderSide, Position, SignalDecision
from stock_trading_bot.strategy.profit_lock import ProfitLock

logger = logging.getLogger(__name__)


class OrderManager:
    def __init__(self, broker, database: TradingDatabase) -> None:
        self.broker = broker
        self.database = database
        self.positions: dict[str, Position] = database.load_positions()

    def reconcile_positions(self) -> None:
        if not hasattr(self.broker, "get_open_positions"):
            return
        broker_positions = self.broker.get_open_positions()
        for symbol, position in broker_positions.items():
            existing = self.positions.get(symbol)
            if existing:
                position.highest_price = max(existing.highest_price, position.highest_price)
                position.stop_lock_price = max(existing.stop_lock_price, position.stop_lock_price)
            self.positions[symbol] = position
            self.database.upsert_position(position)

    def buy(self, decision: SignalDecision, quantity: int) -> Position:
        if not decision.indicators:
            raise ValueError("Buy decision requires technical indicators")
        price = decision.indicators.current_price
        result = self.broker.submit_market_order(decision.symbol, OrderSide.BUY, quantity, price)
        lock = ProfitLock(entry_price=price)
        position = Position(
            symbol=decision.symbol,
            quantity=quantity,
            entry_price=price,
            current_price=price,
            highest_price=price,
            stop_lock_price=float(lock.current_lock_price),
        )
        self.positions[decision.symbol] = position
        self.database.upsert_position(position)
        self.database.record_order(
            OrderRecord(
                symbol=decision.symbol,
                side=OrderSide.BUY,
                quantity=quantity,
                price=price,
                reason=decision.reason,
                news_score=decision.news_score,
                indicators=decision.indicators,
                stop_lock_price=position.stop_lock_price,
            )
        )
        logger.info("BUY %s x%d @ %.2f (%s)", decision.symbol, quantity, price, result.status)
        return position

    def update_position_price(self, symbol: str, current_price: float) -> Position | None:
        position = self.positions.get(symbol)
        if not position:
            return None
        lock = ProfitLock(position.entry_price, position.highest_price, position.stop_lock_price)
        stop_lock_price = lock.update(current_price)
        position.current_price = current_price
        position.highest_price = float(lock.highest_price)
        position.stop_lock_price = stop_lock_price
        self.database.upsert_position(position)
        return position

    def sell(self, decision: SignalDecision) -> None:
        position = self.positions.get(decision.symbol)
        if not position:
            logger.warning("No position to sell for %s", decision.symbol)
            return
        result = self.broker.submit_market_order(
            decision.symbol,
            OrderSide.SELL,
            position.quantity,
            position.current_price,
        )
        pnl = (position.current_price - position.entry_price) * position.quantity
        self.database.record_order(
            OrderRecord(
                symbol=decision.symbol,
                side=OrderSide.SELL,
                quantity=position.quantity,
                price=position.current_price,
                reason=decision.reason,
                news_score=decision.news_score,
                indicators=None,
                stop_lock_price=position.stop_lock_price,
                pnl=pnl,
            )
        )
        del self.positions[decision.symbol]
        self.database.delete_position(decision.symbol)
        logger.info("SELL %s x%d @ %.2f pnl=%.2f (%s)", decision.symbol, position.quantity, position.current_price, pnl, result.status)
