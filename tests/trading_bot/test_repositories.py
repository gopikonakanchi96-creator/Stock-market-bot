from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from trading_bot.app.domain import Instrument, NewsSignal, OrderResult, Position, SignalAction, StrategyDecision
from trading_bot.database.models import Base
from trading_bot.database.repositories import TradingRepository


def repository() -> TradingRepository:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return TradingRepository(sessionmaker(bind=engine, expire_on_commit=False))


def test_repository_logs_signal_news_order_trade_and_position():
    repo = repository()
    news = NewsSignal("Bullish", 55, 0.8, 5, 0.9, ["AAPL strong growth"])
    decision = StrategyDecision(SignalAction.BUY, 0.75, "test buy", 55, 0.8)
    instrument = Instrument("AAPL", "Apple", "US", "United States", "NASDAQ", "USD")
    position = Position(instrument, 10, 100, 101, 101, 90, 90)

    repo.log_news("AAPL", news)
    repo.log_signal("AAPL", decision)
    repo.log_strategy_decision({"ticker": "AAPL", "decision": "BUY"})
    order_id = repo.log_order_result("AAPL", "BUY", 10, 100, "USD", "test", OrderResult("paper-1", True, "filled", "ok", 100))
    repo.log_trade(order_id, realized_pl=0)
    repo.upsert_position(position)
    repo.log_portfolio_history("USD", 100_000)
    repo.log_audit("test", "repository logging")

    counts = repo.latest_counts()

    assert counts["news"] == 1
    assert counts["signals"] == 1
    assert counts["orders"] == 1
    assert counts["trades"] == 1
    assert counts["positions"] == 1
    assert counts["portfolio_history"] == 1
    assert counts["strategy_logs"] == 1
    assert counts["audit_logs"] == 1

