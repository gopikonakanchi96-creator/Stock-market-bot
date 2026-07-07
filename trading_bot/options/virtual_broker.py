from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from trading_bot.options.models import (
    OptionOrderRequest,
    OptionOrderResult,
    OptionPosition,
    OptionSide,
)


@dataclass(frozen=True)
class OptionPaperTrade:
    timestamp: datetime
    contract_symbol: str
    side: OptionSide
    quantity: int
    premium: float
    commission: float
    realized_pl: float = 0.0


@dataclass
class VirtualOptionsBroker:
    starting_cash: float = 25_000.0
    commission_per_contract: float = 0.65
    cash: float = field(init=False)
    positions: dict[str, OptionPosition] = field(default_factory=dict)
    trade_history: list[OptionPaperTrade] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cash = self.starting_cash

    def submit_order(self, request: OptionOrderRequest) -> OptionOrderResult:
        if request.side == OptionSide.BUY:
            return self.buy(request)
        return self.sell(request)

    def buy(self, request: OptionOrderRequest) -> OptionOrderResult:
        if request.quantity <= 0 or request.contract.premium <= 0:
            return OptionOrderResult("", False, "rejected", "Invalid quantity or premium")
        commission = request.quantity * self.commission_per_contract
        cost = request.quantity * request.contract.premium * request.contract.multiplier + commission
        if cost > self.cash:
            return OptionOrderResult("", False, "rejected", "Insufficient virtual options cash")
        self.cash -= cost
        key = request.contract.symbol
        existing = self.positions.get(key)
        if existing:
            total_quantity = existing.quantity + request.quantity
            average_entry = (
                existing.entry_premium * existing.quantity + request.contract.premium * request.quantity
            ) / total_quantity
            existing.quantity = total_quantity
            existing.entry_premium = average_entry
            existing.current_premium = request.contract.premium
        else:
            self.positions[key] = OptionPosition(
                contract=request.contract,
                quantity=request.quantity,
                entry_premium=request.contract.premium,
                current_premium=request.contract.premium,
            )
        self.trade_history.append(
            OptionPaperTrade(
                datetime.now(timezone.utc),
                key,
                OptionSide.BUY,
                request.quantity,
                request.contract.premium,
                commission,
            )
        )
        return OptionOrderResult(
            f"option-paper-{len(self.trade_history)}",
            True,
            "filled",
            request.reason or "Virtual options buy filled",
            request.contract.premium,
        )

    def sell(self, request: OptionOrderRequest) -> OptionOrderResult:
        key = request.contract.symbol
        position = self.positions.get(key)
        if position is None:
            return OptionOrderResult("", False, "rejected", "No open virtual options position")
        quantity = min(request.quantity, position.quantity)
        if quantity <= 0 or request.contract.premium <= 0:
            return OptionOrderResult("", False, "rejected", "Invalid quantity or premium")
        commission = quantity * self.commission_per_contract
        proceeds = quantity * request.contract.premium * request.contract.multiplier - commission
        realized_pl = quantity * (request.contract.premium - position.entry_premium) * request.contract.multiplier
        realized_pl -= commission
        self.cash += proceeds
        position.quantity -= quantity
        position.current_premium = request.contract.premium
        if position.quantity <= 0:
            self.positions.pop(key, None)
        self.trade_history.append(
            OptionPaperTrade(
                datetime.now(timezone.utc),
                key,
                OptionSide.SELL,
                quantity,
                request.contract.premium,
                commission,
                realized_pl,
            )
        )
        return OptionOrderResult(
            f"option-paper-{len(self.trade_history)}",
            True,
            "filled",
            request.reason or "Virtual options sell filled",
            request.contract.premium,
        )

    def update_premium(self, contract_symbol: str, premium: float) -> None:
        position = self.positions.get(contract_symbol)
        if position and premium > 0:
            position.current_premium = premium

    def summary(self) -> dict[str, object]:
        return {
            "cash": self.cash,
            "starting_cash": self.starting_cash,
            "open_positions": [
                {
                    "contract": key,
                    "underlying": position.contract.underlying,
                    "type": position.contract.contract_type.value,
                    "strike": position.contract.strike,
                    "expiration": position.contract.expiration.isoformat(),
                    "quantity": position.quantity,
                    "entry_premium": position.entry_premium,
                    "current_premium": position.current_premium,
                    "market_value": position.market_value,
                    "unrealized_pl": position.unrealized_pl,
                }
                for key, position in self.positions.items()
            ],
            "trade_history": [trade.__dict__ for trade in self.trade_history],
        }

