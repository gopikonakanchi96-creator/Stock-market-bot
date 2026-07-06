from __future__ import annotations

from dataclasses import dataclass


PROFIT_LOCK_LEVELS: tuple[tuple[float, float], ...] = (
    (1.00, 0.80),
    (0.75, 0.55),
    (0.50, 0.35),
    (0.30, 0.18),
    (0.20, 0.10),
    (0.10, 0.03),
)


@dataclass
class DynamicProfitLock:
    entry_price: float
    highest_price: float | None = None
    current_lock: float | None = None

    def __post_init__(self) -> None:
        if self.entry_price <= 0:
            raise ValueError("entry_price must be positive")
        self.highest_price = self.entry_price if self.highest_price is None else self.highest_price
        self.current_lock = self.entry_price * 0.90 if self.current_lock is None else self.current_lock

    def update(self, current_price: float) -> float:
        if current_price <= 0:
            raise ValueError("current_price must be positive")
        self.highest_price = max(float(self.highest_price), current_price)
        profit = (self.highest_price - self.entry_price) / self.entry_price
        candidate = self.entry_price * 0.90
        for profit_threshold, lock_profit in PROFIT_LOCK_LEVELS:
            if profit >= profit_threshold:
                candidate = self.entry_price * (1 + lock_profit)
                break
        self.current_lock = max(float(self.current_lock), candidate)
        return self.current_lock

    def should_sell(self, current_price: float) -> bool:
        return current_price <= float(self.current_lock)

