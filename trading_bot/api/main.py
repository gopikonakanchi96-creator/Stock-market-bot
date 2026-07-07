from __future__ import annotations

try:
    from fastapi import FastAPI
except ImportError:
    FastAPI = None

from trading_bot.app.paper_session import build_application_context
from trading_bot.options import OptionsAnalysisService


def create_app():
    if FastAPI is None:
        raise RuntimeError("FastAPI is not installed. Run: pip install -r requirements.txt")
    app = FastAPI(title="AI Multi-Currency Trading Bot", version="1.0.0")
    context = build_application_context()
    options_service = OptionsAnalysisService(context["settings"].options)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": context["settings"].broker_mode.value}

    @app.get("/markets")
    def markets() -> dict[str, object]:
        return {"markets": context["settings"].markets}

    @app.get("/portfolio/summary")
    def portfolio_summary() -> dict[str, object]:
        return context["portfolio"].summary(context["balances"], context["execution"].positions)

    @app.get("/positions/open")
    def open_positions() -> list[dict[str, object]]:
        return context["portfolio"].summary(context["balances"], context["execution"].positions)["open_positions"]

    @app.get("/cash")
    def cash() -> list[dict[str, object]]:
        return [balance.__dict__ for balance in context["execution"].broker.balances()]

    @app.get("/orders")
    def orders() -> list[dict[str, object]]:
        return [trade.__dict__ for trade in getattr(context["execution"].broker, "trade_history", [])]

    @app.get("/trades")
    def trades() -> list[dict[str, object]]:
        return [trade.__dict__ for trade in getattr(context["execution"].broker, "trade_history", [])]

    @app.get("/performance")
    def performance() -> dict[str, object]:
        return context["portfolio"].summary(context["execution"].broker.balances(), context["execution"].positions)

    @app.get("/risk")
    def risk() -> dict[str, object]:
        exceeded, reason = context["risk"].portfolio_exposure_exceeded(context["execution"].positions, 100_000)
        return {"portfolio_exposure_exceeded": exceeded, "reason": reason}

    @app.get("/backtests/sample")
    def backtest_sample() -> dict[str, object]:
        from trading_bot.backtesting.engine import sample_backtest

        return sample_backtest().__dict__

    @app.get("/ai-decisions/{market_code}/{symbol}")
    def ai_decision(market_code: str, symbol: str) -> dict[str, object]:
        return context["paper_session"].analyze_symbol(market_code, symbol, execute=False)

    @app.get("/options/dashboard")
    def options_dashboard() -> dict[str, object]:
        return options_service.dashboard_summary().__dict__

    @app.get("/options/analyze/{symbol}")
    def options_analyze(symbol: str) -> dict[str, object]:
        return options_service.analyze_symbol(symbol.upper())

    @app.get("/news/{market_code}/{symbol}")
    def news_feed(market_code: str, symbol: str) -> dict[str, object]:
        return context["news"].analyze(symbol, market_code).__dict__

    @app.get("/signals/{market_code}/{symbol}")
    def signal(market_code: str, symbol: str) -> dict[str, object]:
        return context["paper_session"].analyze_symbol(market_code, symbol, execute=False)

    @app.websocket("/ws/portfolio")
    async def portfolio_ws(websocket):
        await websocket.accept()
        await websocket.send_json(context["portfolio"].summary(context["balances"], context["execution"].positions))
        await websocket.close()

    return app


app = create_app() if FastAPI is not None else None
