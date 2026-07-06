import pandas as pd

from trading_bot.config.settings import load_settings
from trading_bot.market_data.providers import DeterministicFallbackProvider, MarketDataProvider, MarketDataRequest
from trading_bot.market_data.service import EnterpriseMarketDataService, _sanitize_error


class FailingProvider(MarketDataProvider):
    name = "Failing"

    def historical_candles(self, request: MarketDataRequest) -> pd.DataFrame:
        raise RuntimeError("provider down")


def test_market_data_fails_over_to_next_provider():
    settings = load_settings("config.yaml")
    service = EnterpriseMarketDataService(
        settings.strategy,
        provider_priority=[],
        providers=[FailingProvider(), DeterministicFallbackProvider()],
    )

    indicators = service.indicators("AAPL", settings.markets["US"])

    assert indicators is not None
    assert indicators.current_price > 0


def test_market_data_cache_reuses_provider_response():
    settings = load_settings("config.yaml")
    provider = DeterministicFallbackProvider()
    service = EnterpriseMarketDataService(settings.strategy, provider_priority=[], providers=[provider])

    first = service.historical_candles("AAPL", settings.markets["US"])
    second = service.historical_candles("AAPL", settings.markets["US"])

    assert first.equals(second)


def test_provider_errors_redact_api_tokens():
    message = "403 url=https://x.test/path?symbol=AAPL&token=secret123&apiKey=secret456&apikey=secret789"

    redacted = _sanitize_error(message)

    assert "secret123" not in redacted
    assert "secret456" not in redacted
    assert "secret789" not in redacted
    assert "token=***" in redacted
