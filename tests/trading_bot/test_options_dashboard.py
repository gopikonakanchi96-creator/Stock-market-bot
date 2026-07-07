from trading_bot.config.settings import load_settings
from trading_bot.options import OptionsAnalysisService


def test_options_dashboard_is_analysis_only():
    settings = load_settings()
    summary = OptionsAnalysisService(settings.options).dashboard_summary()

    assert summary.enabled is True
    assert summary.analysis_only is True
    assert summary.total_candidates == 0
    assert "Options are analysis-only" in " ".join(summary.warnings)


def test_options_symbol_analysis_requires_provider():
    settings = load_settings()
    result = OptionsAnalysisService(settings.options).analyze_symbol("AAPL")

    assert result["analysis_only"] is True
    assert result["status"] == "provider_required"
    assert result["opportunities"] == []

