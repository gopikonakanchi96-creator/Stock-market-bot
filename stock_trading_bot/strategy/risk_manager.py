from __future__ import annotations

from dataclasses import dataclass

from stock_trading_bot.config import RiskConfig
from stock_trading_bot.models import Position


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str
    quantity: int = 0
    notional: float = 0.0


class RiskManager:
    def __init__(self, config: RiskConfig) -> None:
        self.config = config

    def daily_loss_exceeded(self, account_equity: float, start_of_day_equity: float) -> bool:
        if start_of_day_equity <= 0:
            return True
        loss_pct = (start_of_day_equity - account_equity) / start_of_day_equity
        return loss_pct >= self.config.max_daily_loss_pct

    def can_open_position(
        self,
        symbol: str,
        price: float,
        account_equity: float,
        start_of_day_equity: float,
        positions: dict[str, Position],
        trades_today: int,
    ) -> RiskDecision:
        if price <= 0 or account_equity <= 0:
            return RiskDecision(False, "Missing or invalid price/account data")
        if self.daily_loss_exceeded(account_equity, start_of_day_equity):
            return RiskDecision(False, "Daily loss limit hit")
        if trades_today >= self.config.max_trades_per_day:
            return RiskDecision(False, "Max trades per day reached")
        if symbol in positions:
            return RiskDecision(False, "Position already held")
        if len(positions) >= self.config.max_open_positions:
            return RiskDecision(False, "Max open positions reached")

        max_loss_dollars = account_equity * self.config.risk_per_trade_pct
        stop_distance = price * 0.10
        risk_based_qty = int(max_loss_dollars // stop_distance)
        notional_based_qty = int(self.config.default_trade_notional // price)
        exposure_based_qty = int((account_equity * self.config.max_exposure_per_stock_pct) // price)
        quantity = min(risk_based_qty, notional_based_qty, exposure_based_qty)

        if quantity <= 0:
            return RiskDecision(False, "Trade size too small under risk limits")

        notional = quantity * price
        return RiskDecision(True, "Risk checks passed", quantity=quantity, notional=notional)

    def exposure_too_high(self, positions: dict[str, Position], account_equity: float) -> tuple[bool, str]:
        if account_equity <= 0:
            return True, "Invalid account equity"
        total_exposure = sum(position.market_value for position in positions.values())
        if total_exposure > account_equity:
            return True, "Total exposure exceeds account equity"
        for symbol, position in positions.items():
            if position.market_value / account_equity > self.config.max_exposure_per_stock_pct:
                return True, f"{symbol} exceeds max exposure per stock"
        return False, "Exposure within limits"

