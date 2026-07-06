from trading_bot.config.env import load_env_file
from trading_bot.market_data.providers import configured_provider_chain


def test_configured_provider_chain_uses_real_adapters(monkeypatch):
    monkeypatch.setenv("FINNHUB_API_KEY", "test")
    monkeypatch.setenv("POLYGON_API_KEY", "test")
    monkeypatch.setenv("ALPHA_VANTAGE_API_KEY", "test")
    monkeypatch.setenv("TWELVE_DATA_API_KEY", "test")

    providers = configured_provider_chain(["Finnhub", "Polygon", "Alpha Vantage", "Twelve Data"])

    assert [provider.name for provider in providers[:4]] == ["Finnhub", "Polygon", "Alpha Vantage", "Twelve Data"]
    assert providers[-1].name == "DeterministicFallback"


def test_env_loader_keeps_existing_env(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("FINNHUB_API_KEY", "already-set")
    (tmp_path / ".env").write_text("FINNHUB_API_KEY=file-value\n", encoding="utf-8")

    load_env_file()

    import os

    assert os.getenv("FINNHUB_API_KEY") == "already-set"

