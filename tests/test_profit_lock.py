from stock_trading_bot.strategy.profit_lock import ProfitLock


def test_profit_lock_table_and_upward_only_behavior():
    lock = ProfitLock(entry_price=100)

    assert lock.current_lock_price == 90
    assert lock.update(150) == 135
    assert lock.update(120) == 135
    assert lock.update(200) == 180
    assert lock.update(160) == 180


def test_profit_lock_triggers_sell_at_lock():
    lock = ProfitLock(entry_price=100)
    lock.update(150)

    assert lock.should_sell(135)
    assert not lock.should_sell(136)

