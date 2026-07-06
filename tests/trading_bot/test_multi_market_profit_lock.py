from trading_bot.strategy.profit_lock import DynamicProfitLock


def test_dynamic_profit_lock_only_moves_up():
    lock = DynamicProfitLock(entry_price=100)

    assert lock.update(105) == 90
    assert lock.update(150) == 135
    assert lock.update(120) == 135
    assert lock.update(200) == 180
    assert lock.update(160) == 180


def test_dynamic_profit_lock_sell_trigger():
    lock = DynamicProfitLock(entry_price=100)
    lock.update(150)

    assert lock.should_sell(135)
    assert not lock.should_sell(136)

