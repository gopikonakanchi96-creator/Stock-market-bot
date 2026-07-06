from __future__ import annotations

from dataclasses import dataclass

from trading_bot.app.domain import Instrument, Position
from trading_bot.config.settings import RiskSettings
from trading_bot.risk.position_sizing import PositionSizer


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str
    quantity: int = 0
    risk_score: float = 0.0


class PortfolioRiskManager:
    def __init__(self, settings: RiskSettings) -> None:
        self.settings = settings
        self.sizer = PositionSizer()

    def validate_entry(
        self,
        instrument: Instrument,
        price: float,
        equity_native: float,
        positions: dict[str, Position],
        trades_today: int,
        daily_pl_pct: float = 0.0,
        weekly_pl_pct: float = 0.0,
        monthly_drawdown_pct: float = 0.0,
        atr: float = 0.0,
    ) -> RiskDecision:
        if self.settings.emergency_stop:
            return RiskDecision(False, "Emergency stop activated")
        if price <= 0 or equity_native <= 0:
            return RiskDecision(False, "Invalid price or account equity")
        if daily_pl_pct <= -self.settings.max_daily_loss:
            return RiskDecision(False, "Maximum daily loss reached")
        if weekly_pl_pct <= -self.settings.max_weekly_loss:
            return RiskDecision(False, "Maximum weekly loss reached")
        if monthly_drawdown_pct >= self.settings.max_monthly_drawdown:
            return RiskDecision(False, "Maximum monthly drawdown reached")
        if trades_today >= self.settings.max_trades_per_day:
            return RiskDecision(False, "Maximum trades per day reached")
        if instrument.symbol in positions:
            return RiskDecision(False, "Position already held")
        if len(positions) >= self.settings.max_open_positions:
            return RiskDecision(False, "Maximum open positions reached")

        risk_qty = self.sizer.risk_based(equity_native, self.settings.risk_per_trade, price)
        exposure_qty = int((equity_native * self.settings.max_exposure_per_stock) // price)
        atr_qty = self.sizer.atr_based(equity_native, self.settings.risk_per_trade, price, atr) if atr > 0 else risk_qty
        quantity = min(risk_qty, exposure_qty, atr_qty)
        if quantity <= 0:
            return RiskDecision(False, "Position size is zero under risk limits")
        sector_exposure = sum(p.market_value for p in positions.values() if p.instrument.sector == instrument.sector)
        if (sector_exposure + quantity * price) / equity_native > self.settings.max_exposure_per_sector:
            return RiskDecision(False, "Maximum sector exposure exceeded")
        return RiskDecision(True, "Risk checks passed", quantity=quantity, risk_score=0.80)

    def portfolio_exposure_exceeded(self, positions: dict[str, Position], equity_native: float) -> tuple[bool, str]:
        if equity_native <= 0:
            return True, "Invalid account equity"
        for symbol, position in positions.items():
            if position.market_value / equity_native > self.settings.max_exposure_per_stock:
                return True, f"{symbol} exceeds maximum stock exposure"
        return False, "Exposure within limits"

