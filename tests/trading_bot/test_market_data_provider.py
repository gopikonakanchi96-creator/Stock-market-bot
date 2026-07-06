import pandas as pd
from datetime import datetime, timezone

from trading_bot.config.settings import load_settings
from trading_bot.markets.market_data import MarketDataService


class FakeAlpacaProvider:
    def historical_daily_bars(self, symbol: str, limit: int = 120) -> pd.DataFrame:
        close = [100 + index for index in range(limit)]
        return pd.DataFrame(
            {
                "close": close,
                "high": [value * 1.01 for value in close],
                "low": [value * 0.99 for value in close],
                "volume": [1_000_000 + index * 1_000 for index in range(limit)],
            },
            index=pd.date_range(end=datetime.now(timezone.utc), periods=limit, freq="D"),
        )


def test_us_market_uses_alpaca_provider_for_indicators():
    settings = load_settings("config.yaml")
    service = MarketDataService(settings.strategy, alpaca_provider=FakeAlpacaProvider())

    snapshot = service.data_snapshot("AAPL", settings.markets["US"])

    assert snapshot["data_available"] is True
    assert snapshot["is_stale"] is False
    assert snapshot["rows"] >= 120
    assert snapshot["indicators"]["current_price"] == 219
