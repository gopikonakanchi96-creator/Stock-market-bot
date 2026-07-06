from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExchangeRate:
    from_currency: str
    to_currency: str
    rate: float
    source: str = "configured"


class CurrencyService:
    def __init__(self, base_currency: str = "USD", configured_rates: dict[tuple[str, str], float] | None = None) -> None:
        self.base_currency = base_currency
        self._rates = configured_rates or {
            ("USD", "USD"): 1.0,
            ("INR", "INR"): 1.0,
            ("USD", "INR"): 83.0,
            ("INR", "USD"): 1 / 83.0,
        }

    def get_rate(self, from_currency: str, to_currency: str | None = None) -> ExchangeRate:
        to_currency = to_currency or self.base_currency
        if from_currency == to_currency:
            return ExchangeRate(from_currency, to_currency, 1.0)
        rate = self._rates.get((from_currency, to_currency))
        if rate is None:
            raise ValueError(f"Missing exchange rate {from_currency}->{to_currency}")
        return ExchangeRate(from_currency, to_currency, rate)

    def convert(self, amount: float, from_currency: str, to_currency: str | None = None) -> float:
        return amount * self.get_rate(from_currency, to_currency).rate

