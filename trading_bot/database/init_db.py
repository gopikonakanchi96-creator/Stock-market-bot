from __future__ import annotations

from trading_bot.config.env import load_env_file
from trading_bot.config.settings import load_settings
from trading_bot.database.models import Base


def init_database(config_path: str = "config.yaml") -> dict[str, object]:
    load_env_file()
    from sqlalchemy import create_engine, inspect

    settings = load_settings(config_path)
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
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

