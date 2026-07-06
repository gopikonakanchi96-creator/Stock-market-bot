from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from stock_trading_bot.models import OrderRecord, Position


class TradingDatabase:
    def __init__(self, path: str) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    price REAL NOT NULL,
                    reason TEXT NOT NULL,
                    news_score INTEGER,
                    indicators_json TEXT,
                    stop_lock_price REAL,
                    pnl REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS positions (
                    symbol TEXT PRIMARY KEY,
                    quantity INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    current_price REAL NOT NULL,
                    highest_price REAL NOT NULL,
                    stop_lock_price REAL NOT NULL,
                    opened_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def record_order(self, order: OrderRecord) -> None:
        indicators_json = None
        if order.indicators:
            indicators_json = json.dumps(order.indicators.__dict__, default=str)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO orders (
                    timestamp, symbol, side, quantity, price, reason, news_score,
                    indicators_json, stop_lock_price, pnl
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order.timestamp.isoformat(),
                    order.symbol,
                    order.side.value,
                    order.quantity,
                    order.price,
                    order.reason,
                    order.news_score,
                    indicators_json,
                    order.stop_lock_price,
                    order.pnl,
                ),
            )
            conn.commit()

    def trades_today_count(self) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS count FROM orders WHERE date(timestamp) = date('now')"
            ).fetchone()
        return int(row["count"])

    def upsert_position(self, position: Position) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO positions (
                    symbol, quantity, entry_price, current_price, highest_price,
                    stop_lock_price, opened_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                ON CONFLICT(symbol) DO UPDATE SET
                    quantity=excluded.quantity,
                    entry_price=excluded.entry_price,
                    current_price=excluded.current_price,
                    highest_price=excluded.highest_price,
                    stop_lock_price=excluded.stop_lock_price,
                    updated_at=datetime('now')
                """,
                (
                    position.symbol,
                    position.quantity,
                    position.entry_price,
                    position.current_price,
                    position.highest_price,
                    position.stop_lock_price,
                    position.opened_at.isoformat(),
                ),
            )
            conn.commit()

    def delete_position(self, symbol: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM positions WHERE symbol = ?", (symbol,))
            conn.commit()

    def load_positions(self) -> dict[str, Position]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM positions").fetchall()
        return {
            row["symbol"]: Position(
                symbol=row["symbol"],
                quantity=int(row["quantity"]),
                entry_price=float(row["entry_price"]),
                current_price=float(row["current_price"]),
                highest_price=float(row["highest_price"]),
                stop_lock_price=float(row["stop_lock_price"]),
            )
            for row in rows
        }
