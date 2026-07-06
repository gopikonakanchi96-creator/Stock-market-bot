from trading_bot.config.settings import load_settings
from trading_bot.currency.service import CurrencyService


def test_us_and_india_enabled_with_native_currencies():
    settings = load_settings("config.yaml")

    assert settings.markets["US"].enabled
    assert settings.markets["US"].currency == "USD"
    assert settings.markets["US"].exchanges == ["NYSE", "NASDAQ"]
    assert settings.markets["India"].enabled
    assert settings.markets["India"].currency == "INR"
    assert settings.markets["Canada"].enabled is False


def test_currency_service_converts_inr_to_base_usd():
    service = CurrencyService(base_currency="USD")

    assert round(service.convert(8300, "INR", "USD"), 2) == 100.0
    assert service.convert(100, "USD", "USD") == 100

