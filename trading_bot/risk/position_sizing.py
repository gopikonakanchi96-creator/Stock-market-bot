from __future__ import annotations


class PositionSizer:
    def fixed_amount(self, amount: float, price: float) -> int:
        return max(0, int(amount // price)) if price > 0 else 0

    def fixed_percentage(self, equity: float, pct: float, price: float) -> int:
        return self.fixed_amount(equity * pct, price)

    def risk_based(self, equity: float, risk_pct: float, price: float, stop_pct: float = 0.10) -> int:
        if price <= 0 or stop_pct <= 0:
            return 0
        max_loss = equity * risk_pct
        return max(0, int(max_loss // (price * stop_pct)))

    def atr_based(self, equity: float, risk_pct: float, price: float, atr: float, atr_multiple: float = 2.0) -> int:
        if price <= 0 or atr <= 0:
            return 0
        return max(0, int((equity * risk_pct) // (atr * atr_multiple)))

