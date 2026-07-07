from __future__ import annotations

from trading_bot.config.settings import OptionsSettings
from trading_bot.options.models import OptionCandidate, OptionsDashboardSummary


class OptionsAnalysisService:
    """Analysis-only options scanner for Version 1.

    This intentionally does not execute options orders. Real options trading needs
    option-chain data, Greeks, spread checks, assignment risk, and broker support.
    """

    def __init__(self, settings: OptionsSettings) -> None:
        self.settings = settings

    def dashboard_summary(self) -> OptionsDashboardSummary:
        warnings: list[str] = []
        next_steps: list[str] = []
        opportunities: list[OptionCandidate] = []

        if not self.settings.enabled:
            warnings.append("Options analysis is disabled in config.yaml.")
        if self.settings.analysis_only:
            warnings.append("Options are analysis-only. The bot will not place options trades.")
        warnings.append("No real options-chain provider is configured yet, so no tradable contracts are emitted.")

        next_steps.extend(
            [
                "Add an options-chain data provider before scoring contracts.",
                "Add Greeks, bid/ask spread, volume, open-interest, and expiration filters.",
                "Start with covered-call and cash-secured-put analysis before any automated options execution.",
            ]
        )

        return OptionsDashboardSummary(
            enabled=self.settings.enabled,
            analysis_only=self.settings.analysis_only,
            watchlist=self.settings.watchlist,
            total_candidates=len(opportunities),
            opportunities=opportunities,
            warnings=warnings,
            next_steps=next_steps,
        )

    def analyze_symbol(self, symbol: str) -> dict[str, object]:
        if symbol not in self.settings.watchlist:
            return {
                "symbol": symbol,
                "status": "not_in_options_watchlist",
                "analysis_only": self.settings.analysis_only,
                "opportunities": [],
                "warnings": [f"{symbol} is not in options.watchlist."],
            }
        return {
            "symbol": symbol,
            "status": "provider_required",
            "analysis_only": self.settings.analysis_only,
            "opportunities": [],
            "warnings": [
                "Options-chain provider is not configured yet.",
                "No options trades will be placed.",
            ],
            "filters": {
                "min_days_to_expiration": self.settings.min_days_to_expiration,
                "max_days_to_expiration": self.settings.max_days_to_expiration,
                "max_contract_price": self.settings.max_contract_price,
                "min_open_interest": self.settings.min_open_interest,
                "min_volume": self.settings.min_volume,
            },
        }

