from __future__ import annotations

import argparse
import logging
from pathlib import Path

from stock_trading_bot.backtesting.backtest import run_backtest
from stock_trading_bot.broker import AlpacaBrokerClient, MockBrokerClient
from stock_trading_bot.config import AppConfig, load_config
from stock_trading_bot.data.market_data import AlpacaMarketData, MockMarketData
from stock_trading_bot.data.news_data import AlpacaNewsData, MockNewsData
from stock_trading_bot.database import TradingDatabase
from stock_trading_bot.execution.order_manager import OrderManager
from stock_trading_bot.strategy.risk_manager import RiskManager
from stock_trading_bot.strategy.signal_engine import SignalEngine


def setup_logging() -> None:
    Path("stock_trading_bot/logs").mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
        handlers=[
            logging.FileHandler("stock_trading_bot/logs/trading_bot.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def run_paper_cycle(config: AppConfig, use_mock_data: bool = False) -> None:
    logger = logging.getLogger("paper_cycle")
    if config.emergency_stop:
        logger.warning("Emergency stop is enabled. New buys are disabled.")

    broker = MockBrokerClient() if use_mock_data else AlpacaBrokerClient(config.broker)
    market_data = MockMarketData(config.strategy) if use_mock_data else AlpacaMarketData(config.strategy)
    news_data = MockNewsData() if use_mock_data else AlpacaNewsData()
    database = TradingDatabase(config.database_path)
    risk_manager = RiskManager(config.risk)
    signal_engine = SignalEngine(config.strategy)
    order_manager = OrderManager(broker, database)
    order_manager.reconcile_positions()

    account_equity = broker.get_account_equity()
    start_of_day_equity = account_equity
    trades_today = database.trades_today_count()

    logger.info("Starting paper cycle. equity=%.2f watchlist=%s", account_equity, ",".join(config.watchlist))
    for symbol in config.watchlist:
        indicators = market_data.get_indicators(symbol)
        sentiment = news_data.get_sentiment(symbol)
        if indicators:
            order_manager.update_position_price(symbol, indicators.current_price)

        exposure_high, exposure_reason = risk_manager.exposure_too_high(order_manager.positions, account_equity)
        position = order_manager.positions.get(symbol)
        if position:
            sell_decision = signal_engine.evaluate_sell(position, sentiment, exposure_high, exposure_reason)
            logger.info("%s sell-check: %s", symbol, sell_decision.reason)
            if sell_decision.should_trade:
                order_manager.sell(sell_decision)
            continue

        buy_decision = signal_engine.evaluate_buy(symbol, indicators, sentiment, order_manager.positions)
        if config.emergency_stop:
            logger.info("%s skipped: emergency stop enabled", symbol)
            continue
        if not buy_decision.should_trade:
            logger.info("%s skipped: %s", symbol, buy_decision.reason)
            continue

        risk_decision = risk_manager.can_open_position(
            symbol=symbol,
            price=indicators.current_price if indicators else 0,
            account_equity=account_equity,
            start_of_day_equity=start_of_day_equity,
            positions=order_manager.positions,
            trades_today=trades_today,
        )
        if not risk_decision.allowed:
            logger.info("%s skipped by risk manager: %s", symbol, risk_decision.reason)
            continue
        order_manager.buy(buy_decision, risk_decision.quantity)
        trades_today += 1

    logger.info("Paper cycle complete. open_positions=%s", list(order_manager.positions))


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(description="Paper-first stock trading bot")
    parser.add_argument("--config", default="stock_trading_bot/config.yaml")
    parser.add_argument("--mode", choices=["paper", "example", "backtest"], default="example")
    parser.add_argument("--csv", help="Historical CSV for backtest with close and volume columns")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.mode == "backtest":
        report = run_backtest(config, csv_path=args.csv)
        for key, value in report.items():
            print(f"{key}: {value}")
    elif args.mode == "paper":
        run_paper_cycle(config, use_mock_data=False)
    else:
        run_paper_cycle(config, use_mock_data=True)


if __name__ == "__main__":
    main()
