from __future__ import annotations

from trading_bot.config.settings import load_settings
from trading_bot.database.models import Base


def create_engine_and_tables(config_path: str = "config.yaml"):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    settings = load_settings(config_path)
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine)

