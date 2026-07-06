from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class NewsArticle:
    title: str
    url: str
    source: str
    published_at: datetime
    category: str
    reliability: float


class NewsProvider(ABC):
    name: str

    @abstractmethod
    def collect(self, symbol: str | None = None, country: str | None = None) -> list[NewsArticle]:
        raise NotImplementedError


class PlaceholderNewsProvider(NewsProvider):
    def __init__(self, name: str, reliability: float) -> None:
        self.name = name
        self.reliability = reliability

    def collect(self, symbol: str | None = None, country: str | None = None) -> list[NewsArticle]:
        ticker = symbol or "market"
        now = datetime.now(timezone.utc)
        return [
            NewsArticle(
                title=f"{ticker} shows resilient demand and constructive analyst commentary",
                url=f"https://example.com/{self.name}/{ticker}",
                source=self.name,
                published_at=now,
                category="company",
                reliability=self.reliability,
            )
        ]


def default_news_providers() -> list[NewsProvider]:
    return [
        PlaceholderNewsProvider("Finnhub News", 0.90),
        PlaceholderNewsProvider("MarketWatch", 0.82),
        PlaceholderNewsProvider("Yahoo Finance", 0.78),
        PlaceholderNewsProvider("Financial Modeling Prep", 0.75),
        PlaceholderNewsProvider("RSS feeds", 0.60),
    ]

