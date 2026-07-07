from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import date, datetime, time
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from trading_bot.app.domain import IndicatorSet, NewsSignal, OrderResult, Position, StrategyDecision
from trading_bot.config.env import load_env_file
from trading_bot.config.settings import load_settings
from trading_bot.database.models import (
    AuditLog,
    Base,
    News,
    Order,
    PortfolioHistory,
    Position as PositionModel,
    RiskEvent,
    Signal,
    StrategyLog,
    Trade,
)


def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return asdict(value)
    return str(value)


def to_json(value: Any) -> str:
    return json.dumps(value, default=_json_default, sort_keys=True)


class TradingRepository:
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self.session_factory = session_factory

    @classmethod
    def from_config(cls, config_path: str = "config.yaml") -> "TradingRepository":
        load_env_file()
        settings = load_settings(config_path)
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        Base.metadata.create_all(engine)
        return cls(sessionmaker(bind=engine, expire_on_commit=False))

    def log_news(self, symbol: str, news: NewsSignal) -> None:
        with self.session_factory() as session:
            for headline in news.headlines:
                session.add(News(symbol=symbol, score=news.score, confidence=news.confidence, headline=headline))
            session.commit()

    def log_signal(self, symbol: str, decision: StrategyDecision) -> None:
        with self.session_factory() as session:
            session.add(
                Signal(
                    symbol=symbol,
                    decision=decision.action.value,
                    confidence=decision.confidence,
                    reason=decision.explanation,
                )
            )
            session.commit()

    def log_strategy_decision(self, payload: dict[str, Any]) -> None:
        with self.session_factory() as session:
            session.add(StrategyLog(message=to_json(payload)))
            session.commit()

    def log_risk_event(self, severity: str, reason: str, payload: dict[str, Any] | None = None) -> None:
        message = reason if payload is None else f"{reason} | {to_json(payload)}"
        with self.session_factory() as session:
            session.add(RiskEvent(severity=severity, reason=message))
            session.commit()

    def log_order_result(
        self,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        currency: str,
        reason: str,
        result: OrderResult,
    ) -> int:
        with self.session_factory() as session:
            order = Order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                currency=currency,
                status=result.status,
                reason=f"{reason} | {result.reason}",
            )
            session.add(order)
            session.commit()
            return int(order.id)

    def log_trade(self, order_id: int, realized_pl: float = 0.0) -> None:
        with self.session_factory() as session:
            session.add(Trade(order_id=order_id, realized_pl=realized_pl))
            session.commit()

    def upsert_position(self, position: Position) -> None:
        with self.session_factory() as session:
            existing = (
                session.query(PositionModel)
                .filter(
                    PositionModel.symbol == position.instrument.symbol,
                    PositionModel.currency == position.instrument.currency,
                )
                .one_or_none()
            )
            if existing is None:
                existing = PositionModel(
                    symbol=position.instrument.symbol,
                    country=position.instrument.country,
                    exchange=position.instrument.exchange,
                    currency=position.instrument.currency,
                    quantity=position.quantity,
                    entry_price=position.entry_price,
                    current_price=position.current_price,
                    highest_price=position.highest_price,
                    stop_loss=position.stop_loss,
                    profit_lock=position.profit_lock,
                )
                session.add(existing)
            else:
                existing.quantity = position.quantity
                existing.current_price = position.current_price
                existing.highest_price = position.highest_price
                existing.stop_loss = position.stop_loss
                existing.profit_lock = position.profit_lock
            session.commit()

    def log_portfolio_history(self, base_currency: str, value: float) -> None:
        with self.session_factory() as session:
            session.add(PortfolioHistory(base_currency=base_currency, value=value))
            session.commit()

    def log_audit(self, actor: str, action: str, payload: dict[str, Any] | None = None) -> None:
        message = action if payload is None else f"{action} | {to_json(payload)}"
        with self.session_factory() as session:
            session.add(AuditLog(actor=actor, action=message))
            session.commit()

    def latest_counts(self) -> dict[str, int]:
        with self.session_factory() as session:
            return {
                "news": session.query(News).count(),
                "signals": session.query(Signal).count(),
                "orders": session.query(Order).count(),
                "trades": session.query(Trade).count(),
                "positions": session.query(PositionModel).count(),
                "portfolio_history": session.query(PortfolioHistory).count(),
                "strategy_logs": session.query(StrategyLog).count(),
                "risk_events": session.query(RiskEvent).count(),
                "audit_logs": session.query(AuditLog).count(),
            }

    def daily_report_data(self, report_date: date) -> dict[str, Any]:
        start = datetime.combine(report_date, time.min)
        end = datetime.combine(report_date, time.max)
        with self.session_factory() as session:
            orders = (
                session.query(Order)
                .filter(Order.created_at >= start, Order.created_at <= end)
                .order_by(Order.created_at.asc())
                .all()
            )
            trades = session.query(Trade).filter(Trade.created_at >= start, Trade.created_at <= end).all()
            trade_pnl_by_order: dict[int, float] = {}
            for trade in trades:
                trade_pnl_by_order[trade.order_id] = trade_pnl_by_order.get(trade.order_id, 0.0) + float(trade.realized_pl or 0.0)

            positions = session.query(PositionModel).order_by(PositionModel.symbol.asc()).all()
            latest_portfolio = (
                session.query(PortfolioHistory)
                .filter(PortfolioHistory.timestamp <= end)
                .order_by(PortfolioHistory.timestamp.desc())
                .first()
            )
            signals = (
                session.query(Signal)
                .filter(Signal.created_at >= start, Signal.created_at <= end)
                .order_by(Signal.created_at.asc())
                .all()
            )
            risk_events = (
                session.query(RiskEvent)
                .filter(RiskEvent.created_at >= start, RiskEvent.created_at <= end)
                .order_by(RiskEvent.created_at.asc())
                .all()
            )
            return {
                "orders": [
                    {
                        "symbol": order.symbol,
                        "side": order.side,
                        "quantity": order.quantity,
                        "price": order.price,
                        "currency": order.currency,
                        "status": order.status,
                        "reason": order.reason,
                        "pnl": trade_pnl_by_order.get(order.id, 0.0),
                        "created_at": order.created_at,
                    }
                    for order in orders
                ],
                "positions": [
                    {
                        "symbol": position.symbol,
                        "country": position.country,
                        "exchange": position.exchange,
                        "currency": position.currency,
                        "quantity": position.quantity,
                        "entry_price": position.entry_price,
                        "current_price": position.current_price,
                        "highest_price": position.highest_price,
                        "stop_loss": position.stop_loss,
                        "profit_lock": position.profit_lock,
                    }
                    for position in positions
                ],
                "portfolio_value": float(latest_portfolio.value) if latest_portfolio else 0.0,
                "portfolio_base_currency": latest_portfolio.base_currency if latest_portfolio else "USD",
                "signal_counts": {
                    decision: sum(1 for signal in signals if signal.decision == decision)
                    for decision in sorted({signal.decision for signal in signals})
                },
                "risk_events": [
                    {"severity": event.severity, "reason": event.reason, "created_at": event.created_at}
                    for event in risk_events
                ],
            }
