from __future__ import annotations

from dataclasses import dataclass


PROFIT_LOCK_TABLE: tuple[tuple[float, float], ...] = (
    (1.00, 0.80),
    (0.75, 0.55),
    (0.50, 0.35),
    (0.30, 0.18),
    (0.20, 0.10),
    (0.10, 0.03),
)


@dataclass
class ProfitLock:
    entry_price: float
    highest_price: float | None = None
    current_lock_price: float | None = None

    def __post_init__(self) -> None:
        if self.entry_price <= 0:
            raise ValueError("entry_price must be positive")
        if self.highest_price is None:
            self.highest_price = self.entry_price
        initial_stop = self.entry_price * 0.90
        if self.current_lock_price is None:
            self.current_lock_price = initial_stop
        else:
            self.current_lock_price = max(self.current_lock_price, initial_stop)

    def update(self, current_price: float) -> float:
        if current_price <= 0:
            raise ValueError("current_price must be positive")

        self.highest_price = max(float(self.highest_price), current_price)
        profit_pct = (self.highest_price - self.entry_price) / self.entry_price
        candidate_lock = self.entry_price * 0.90

        for profit_threshold, lock_profit in PROFIT_LOCK_TABLE:
            if profit_pct >= profit_threshold:
                candidate_lock = self.entry_price * (1 + lock_profit)
                break

        self.current_lock_price = max(float(self.current_lock_price), candidate_lock)
        return self.current_lock_price

    def should_sell(self, current_price: float) -> bool:
        return current_price <= float(self.current_lock_price)


def calculate_lock_price(
    entry_price: float,
    highest_price: float,
    current_lock_price: float | None = None,
) -> float:
    lock = ProfitLock(
        entry_price=entry_price,
        highest_price=highest_price,
        current_lock_price=current_lock_price,
    )
    return lock.update(highest_price)

