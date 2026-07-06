from stock_trading_bot.config import RiskConfig
from stock_trading_bot.models import Position
from stock_trading_bot.strategy.risk_manager import RiskManager


def config() -> RiskConfig:
    return RiskConfig(
        risk_per_trade_pct=0.01,
        max_open_positions=2,
        max_exposure_per_stock_pct=0.20,
        max_daily_loss_pct=0.03,
        max_trades_per_day=3,
        default_trade_notional=1_000,
    )


def test_position_size_respects_risk_and_notional_limits():
    manager = RiskManager(config())

    decision = manager.can_open_position(
        symbol="AAPL",
        price=100,
        account_equity=100_000,
        start_of_day_equity=100_000,
        positions={},
        trades_today=0,
    )

    assert decision.allowed
    assert decision.quantity == 10
    assert decision.notional == 1_000


def test_daily_loss_blocks_new_trades():
    manager = RiskManager(config())

    decision = manager.can_open_position(
        symbol="AAPL",
        price=100,
        account_equity=96_000,
        start_of_day_equity=100_000,
        positions={},
        trades_today=0,
    )

    assert not decision.allowed
    assert decision.reason == "Daily loss limit hit"


def test_exposure_check_flags_oversized_position():
    manager = RiskManager(config())
    positions = {
        "AAPL": Position(
            symbol="AAPL",
            quantity=300,
            entry_price=100,
            current_price=100,
            highest_price=100,
            stop_lock_price=90,
        )
    }

    too_high, reason = manager.exposure_too_high(positions, account_equity=100_000)

    assert too_high
    assert "AAPL" in reason

