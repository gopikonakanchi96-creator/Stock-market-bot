from __future__ import annotations

from pathlib import Path

import pandas as pd

from stock_trading_bot.config import AppConfig
from stock_trading_bot.strategy.profit_lock import ProfitLock


def _sample_history() -> pd.DataFrame:
    closes = [100, 101, 103, 106, 111, 119, 124, 130, 142, 151, 147, 140, 135, 133]
    volumes = [1_000_000 + i * 10_000 for i in range(len(closes))]
    return pd.DataFrame({"close": closes, "volume": volumes})


def max_drawdown(equity_curve: list[float]) -> float:
    peak = equity_curve[0]
    worst = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        drawdown = (peak - value) / peak if peak else 0.0
        worst = max(worst, drawdown)
    return worst


def run_backtest(config: AppConfig, csv_path: str | None = None) -> dict[str, float | int | str]:
    data = pd.read_csv(csv_path) if csv_path else _sample_history()
    if "close" not in data.columns:
        raise ValueError("Backtest CSV must include a close column")

    initial_equity = 100_000.0
    cash = initial_equity
    quantity = 0
    entry_price = 0.0
    lock: ProfitLock | None = None
    trades: list[float] = []
    equity_curve = [initial_equity]

    for index, row in data.iterrows():
        price = float(row["close"])
        if quantity == 0 and index >= 2 and price > float(data["close"].iloc[index - 1]):
            quantity = int(config.risk.default_trade_notional // price)
            if quantity > 0:
                entry_price = price
                cash -= quantity * price
                lock = ProfitLock(entry_price)
        elif quantity > 0 and lock:
            lock.update(price)
            if lock.should_sell(price) or index == len(data) - 1:
                pnl = (price - entry_price) * quantity
                trades.append(pnl)
                cash += quantity * price
                quantity = 0
                entry_price = 0.0
                lock = None
        position_value = quantity * price
        equity_curve.append(cash + position_value)

    wins = [trade for trade in trades if trade > 0]
    losses = [trade for trade in trades if trade <= 0]
    total_return = (equity_curve[-1] - initial_equity) / initial_equity
    return {
        "total_return_pct": round(total_return * 100, 2),
        "win_rate_pct": round((len(wins) / len(trades) * 100) if trades else 0.0, 2),
        "average_win": round(sum(wins) / len(wins), 2) if wins else 0.0,
        "average_loss": round(sum(losses) / len(losses), 2) if losses else 0.0,
        "max_drawdown_pct": round(max_drawdown(equity_curve) * 100, 2),
        "number_of_trades": len(trades),
        "best_trade": round(max(trades), 2) if trades else 0.0,
        "worst_trade": round(min(trades), 2) if trades else 0.0,
        "data_source": str(Path(csv_path)) if csv_path else "built-in sample",
    }

