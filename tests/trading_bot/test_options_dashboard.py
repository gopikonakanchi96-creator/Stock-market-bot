from datetime import date

from trading_bot.config.settings import load_settings
from trading_bot.options import (
    OptionContract,
    OptionOrderRequest,
    OptionSide,
    OptionType,
    OptionsAnalysisService,
    VirtualOptionsBroker,
)


def test_options_dashboard_is_analysis_only():
    settings = load_settings()
    summary = OptionsAnalysisService(settings.options).dashboard_summary()

    assert summary.enabled is True
    assert summary.analysis_only is False
    assert summary.paper_trading_enabled is True
    assert summary.total_candidates == 0
    assert "Options paper trading is enabled" in " ".join(summary.warnings)


def test_options_symbol_analysis_requires_provider():
    settings = load_settings()
    result = OptionsAnalysisService(settings.options).analyze_symbol("AAPL")

    assert result["analysis_only"] is False
    assert result["paper_trading_enabled"] is True
    assert result["status"] == "provider_required"
    assert result["opportunities"] == []


def test_virtual_options_broker_buys_and_sells_contract():
    broker = VirtualOptionsBroker(starting_cash=5_000, commission_per_contract=0.65)
    contract = OptionContract("AAPL", OptionType.CALL, 300, date(2026, 8, 21), premium=2.5)

    buy = broker.submit_order(OptionOrderRequest(contract, OptionSide.BUY, 2, "test buy"))

    assert buy.accepted
    assert contract.symbol in broker.positions
    assert broker.cash < 5_000

    sell_contract = OptionContract("AAPL", OptionType.CALL, 300, date(2026, 8, 21), premium=3.0)
    sell = broker.submit_order(OptionOrderRequest(sell_contract, OptionSide.SELL, 1, "test sell"))

    assert sell.accepted
    assert broker.positions[contract.symbol].quantity == 1
    assert broker.trade_history[-1].realized_pl > 0
