from __future__ import annotations

from trading_bot.config.env import load_env_file
from trading_bot.config.settings import load_settings
from trading_bot.database.models import Base


TIMESTAMP_MIGRATIONS = {
    "trades": ["created_at"],
    "news": ["created_at"],
    "signals": ["created_at"],
    "backtests": ["created_at"],
    "risk_events": ["created_at"],
}


def _ensure_timestamp_columns(engine) -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())
    with engine.begin() as connection:
        for table, columns in TIMESTAMP_MIGRATIONS.items():
            if table not in table_names:
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table)}
            for column in columns:
                if column not in existing_columns:
                    connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} TIMESTAMP"))
                    connection.execute(text(f"UPDATE {table} SET {column} = CURRENT_TIMESTAMP WHERE {column} IS NULL"))


def init_database(config_path: str = "config.yaml") -> dict[str, object]:
    load_env_file()
    from sqlalchemy import create_engine, inspect

    settings = load_settings(config_path)
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    _ensure_timestamp_columns(engine)
    inspector = inspect(engine)
    return {
        "database_url": settings.database_url.replace("trader:trader@", "trader:***@"),
        "tables": sorted(inspector.get_table_names()),
    }


def main() -> None:
    result = init_database()
    print("Database initialized")
    print(f"URL: {result['database_url']}")
    print("Tables:")
    for table in result["tables"]:
        print(f"- {table}")


if __name__ == "__main__":
    main()
