from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from trading_bot.strategy.profit_lock import DynamicProfitLock


@dataclass(frozen=True)
class BacktestReport:
    annual_return: float
    cagr: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    win_rate: float
    average_win: float
    average_loss: float
    profit_factor: float
    expectancy: float
    number_of_trades: int
    equity_curve: list[float]
    trade_history: list[dict[str, float]]


class BacktestEngine:
    def run(self, prices: pd.DataFrame, starting_cash: float = 100_000, trade_amount: float = 10_000) -> BacktestReport:
        if "close" not in prices.columns:
            raise ValueError("Backtest prices must include close column")
        cash = starting_cash
        quantity = 0
        entry = 0.0
        lock: DynamicProfitLock | None = None
        trades: list[dict[str, float]] = []
        equity_curve = [starting_cash]

        for index, row in prices.reset_index(drop=True).iterrows():
            price = float(row["close"])
            if quantity == 0 and index >= 2 and price > float(prices["close"].iloc[index - 1]):
                quantity = int(trade_amount // price)
                if quantity:
                    entry = price
                    cash -= quantity * price
                    lock = DynamicProfitLock(entry)
            elif quantity and lock:
                lock.update(price)
                if lock.should_sell(price) or index == len(prices) - 1:
                    pnl = (price - entry) * quantity
                    trades.append({"entry": entry, "exit": price, "quantity": quantity, "pnl": pnl})
                    cash += quantity * price
                    quantity = 0
                    lock = None
            equity_curve.append(cash + quantity * price)

        returns = pd.Series(equity_curve).pct_change().dropna()
        downside = returns[returns < 0]
        drawdowns = self._drawdowns(equity_curve)
        wins = [trade["pnl"] for trade in trades if trade["pnl"] > 0]
        losses = [trade["pnl"] for trade in trades if trade["pnl"] <= 0]
        gross_win = sum(wins)
        gross_loss = abs(sum(losses))
        years = max(len(prices) / 252, 1 / 252)
        ending = equity_curve[-1]
        cagr = (ending / starting_cash) ** (1 / years) - 1
        expectancy = (sum(t["pnl"] for t in trades) / len(trades)) if trades else 0.0
        return BacktestReport(
            annual_return=float(returns.mean() * 252) if not returns.empty else 0.0,
            cagr=float(cagr),
            sharpe_ratio=float((returns.mean() / returns.std()) * (252**0.5)) if len(returns) > 1 and returns.std() else 0.0,
            sortino_ratio=float((returns.mean() / downside.std()) * (252**0.5)) if len(downside) > 1 and downside.std() else 0.0,
            max_drawdown=max(drawdowns) if drawdowns else 0.0,
            win_rate=(len(wins) / len(trades)) if trades else 0.0,
            average_win=(gross_win / len(wins)) if wins else 0.0,
            average_loss=(sum(losses) / len(losses)) if losses else 0.0,
            profit_factor=(gross_win / gross_loss) if gross_loss else float("inf") if gross_win else 0.0,
            expectancy=expectancy,
            number_of_trades=len(trades),
            equity_curve=[round(v, 2) for v in equity_curve],
            trade_history=trades,
        )

    @staticmethod
    def _drawdowns(equity_curve: list[float]) -> list[float]:
        peak = equity_curve[0]
        drawdowns = []
        for value in equity_curve:
            peak = max(peak, value)
            drawdowns.append((peak - value) / peak if peak else 0.0)
        return drawdowns


def sample_backtest() -> BacktestReport:
    prices = pd.DataFrame({"close": [100, 101, 103, 106, 110, 118, 125, 134, 151, 147, 139, 135]})
    return BacktestEngine().run(prices)

