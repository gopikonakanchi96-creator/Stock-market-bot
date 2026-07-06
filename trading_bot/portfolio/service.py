from __future__ import annotations

from trading_bot.app.domain import AccountBalance, Position
from trading_bot.currency.service import CurrencyService


class PortfolioService:
    def __init__(self, currency_service: CurrencyService) -> None:
        self.currency_service = currency_service

    def summary(self, balances: list[AccountBalance], positions: dict[str, Position]) -> dict[str, object]:
        cash_by_currency = {balance.currency: balance.cash for balance in balances}
        position_value_native: dict[str, float] = {}
        total_base = 0.0
        for balance in balances:
            total_base += self.currency_service.convert(balance.cash, balance.currency)
        holdings = []
        for position in positions.values():
            currency = position.instrument.currency
            position_value_native[currency] = position_value_native.get(currency, 0.0) + position.market_value
            total_base += self.currency_service.convert(position.market_value, currency)
            holdings.append(
                {
                    "symbol": position.instrument.symbol,
                    "country": position.instrument.country,
                    "exchange": position.instrument.exchange,
                    "currency": currency,
                    "quantity": position.quantity,
                    "entry_price": position.entry_price,
                    "current_price": position.current_price,
                    "unrealized_pl": position.unrealized_pl,
                    "stop_loss": position.stop_loss,
                    "profit_lock": position.profit_lock,
                    "highest_price": position.highest_price,
                }
            )
        return {
            "base_currency": self.currency_service.base_currency,
            "cash_balances": cash_by_currency,
            "position_value_native": position_value_native,
            "portfolio_value_base": round(total_base, 2),
            "open_positions": holdings,
        }

