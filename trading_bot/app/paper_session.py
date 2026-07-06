from __future__ import annotations

from trading_bot.app.domain import Instrument, OrderRequest, OrderSide, SignalAction
from trading_bot.config.env import load_env_file
from trading_bot.config.settings import AppSettings, load_settings
from trading_bot.currency.service import CurrencyService
from trading_bot.execution.order_service import ExecutionService
from trading_bot.market_data.service import EnterpriseMarketDataService
from trading_bot.monitoring.logging import configure_logging, get_logger
from trading_bot.news.service import AINewsService
from trading_bot.paper_broker import VirtualBroker
from trading_bot.portfolio.service import PortfolioService
from trading_bot.risk.manager import PortfolioRiskManager
from trading_bot.strategy.signal_engine import AISignalEngine


class PaperTradingSession:
    def __init__(
        self,
        settings: AppSettings,
        market_data: EnterpriseMarketDataService,
        news: AINewsService,
        risk: PortfolioRiskManager,
        signal_engine: AISignalEngine,
        execution: ExecutionService,
    ) -> None:
        self.settings = settings
        self.market_data = market_data
        self.news = news
        self.risk = risk
        self.signal_engine = signal_engine
        self.execution = execution
        self.logger = get_logger("paper_session")

    def _instrument(self, market_code: str, symbol: str) -> Instrument:
        market = self.settings.markets[market_code]
        exchange = market.exchanges[0] if market.exchanges else market_code
        return Instrument(
            symbol=symbol,
            name=symbol,
            market=market.code,
            country=market.country,
            exchange=exchange,
            currency=market.currency,
        )

    def analyze_symbol(self, market_code: str, symbol: str, execute: bool = True) -> dict[str, object]:
        market = self.settings.markets[market_code]
        instrument = self._instrument(market_code, symbol)
        indicators = self.market_data.indicators(symbol, market)
        news_signal = self.news.analyze(symbol, market_code)
        already_held = symbol in self.execution.positions
        market_open = self.market_data.market_is_open(market)
        risk_preview = self.risk.validate_entry(
            instrument=instrument,
            price=indicators.current_price if indicators else 0,
            equity_native=100_000 if market.currency == "USD" else 2_500_000,
            positions=self.execution.positions,
            trades_today=0,
            atr=indicators.atr if indicators else 0,
        )
        decision = self.signal_engine.decide(
            indicators=indicators,
            news=news_signal,
            risk_score=risk_preview.risk_score,
            market_open=market_open,
            already_held=already_held,
        )
        result = None
        if execute and decision.action == SignalAction.BUY and risk_preview.allowed and indicators:
            request = OrderRequest(
                instrument=instrument,
                side=OrderSide.BUY,
                quantity=risk_preview.quantity,
                estimated_price=indicators.current_price,
                reason=decision.explanation,
                decision=decision,
            )
            result = self.execution.execute(request)
        elif decision.action == SignalAction.BUY and not risk_preview.allowed:
            decision = decision.__class__(
                SignalAction.WAIT,
                decision.confidence,
                f"Risk rejected trade: {risk_preview.reason}",
                decision.news_score,
                risk_preview.risk_score,
                decision.metadata,
            )

        payload = {
            "time": indicators.timestamp.isoformat() if indicators else None,
            "country": market.country,
            "currency": market.currency,
            "ticker": symbol,
            "signal": decision.action.value,
            "news_score": news_signal.score,
            "news_confidence": news_signal.confidence,
            "indicators": indicators.__dict__ if indicators else None,
            "reason": decision.explanation,
            "risk_score": risk_preview.risk_score,
            "decision": decision.action.value,
            "execution_result": result.__dict__ if result else None,
        }
        if hasattr(self.logger, "info"):
            self.logger.info("strategy_decision", **payload) if self.logger.__class__.__module__.startswith("structlog") else self.logger.info(payload)
        return payload

    def run_once(self) -> list[dict[str, object]]:
        decisions = []
        for market_code, market in self.settings.markets.items():
            if not market.enabled:
                continue
            for symbol in self.settings.watchlists.get(market_code, []):
                decisions.append(self.analyze_symbol(market_code, symbol))
        return decisions


def build_application_context(config_path: str = "config.yaml") -> dict[str, object]:
    load_env_file()
    settings = load_settings(config_path)
    market_data = EnterpriseMarketDataService(settings.strategy, settings.market_data_provider_priority)
    news = AINewsService()
    risk = PortfolioRiskManager(settings.risk)
    signal_engine = AISignalEngine(settings.strategy)
    broker = VirtualBroker(starting_balances=settings.paper_starting_balances)
    execution = ExecutionService(broker)
    currency = CurrencyService(settings.base_currency)
    portfolio = PortfolioService(currency)
    balances = broker.balances()
    session = PaperTradingSession(settings, market_data, news, risk, signal_engine, execution)
    return {
        "settings": settings,
        "market_data": market_data,
        "news": news,
        "risk": risk,
        "signal_engine": signal_engine,
        "execution": execution,
        "currency": currency,
        "portfolio": portfolio,
        "balances": balances,
        "paper_session": session,
    }


def run_sample_paper_session(config_path: str = "config.yaml") -> list[dict[str, object]]:
    configure_logging()
    context = build_application_context(config_path)
    return context["paper_session"].run_once()
