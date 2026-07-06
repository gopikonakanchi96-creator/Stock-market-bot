# AI Multi-Currency Stock Trading Bot

This repository now contains a production-oriented `trading_bot/` platform for paper-first, multi-country, multi-currency trading. Version 1 enables:

- United States, USD, NYSE/NASDAQ, Alpaca paper broker
- India, INR, NSE/BSE, placeholder paper broker interface

The older compact prototype remains in `stock_trading_bot/`.

## Safety

Live trading is disabled by default. `live_trading: false` in `config.yaml`, `ALLOW_LIVE_TRADING=false`, and the Alpaca broker rejects live mode in Version 1. If required market data is missing, AI/news confidence is low, or risk rules fail, trades are rejected or skipped and logged.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set paper credentials in `.env` for Alpaca paper execution.

## Run

```powershell
pytest
python -m trading_bot.app.cli --mode paper-sample --config config.yaml
python -m trading_bot.app.cli --mode backtest --config config.yaml
python -m trading_bot.app.cli --mode check-alpaca
python -m trading_bot.app.cli --mode check-market-data --market US --symbol AAPL
python -m trading_bot.app.cli --mode send-daily-report --to gkkcsp2023@gmail.com
uvicorn trading_bot.api.main:app --reload
```

Docker:

```powershell
docker compose up --build
```

FastAPI docs: `http://localhost:8000/docs`

## Architecture

`trading_bot/` is split into replaceable services:

- `market_data`: provider-priority service with cache and failover. Default priority is Finnhub, Polygon, Alpha Vantage, Twelve Data, then deterministic fallback.
- `news`: provider-priority collection, deduplication, freshness, reliability, and sentiment input.
- `ai`: AI analysis service that summarizes/reasons/recommends but never executes trades.
- `paper_broker`: internal virtual broker for no-real-money simulation.
- `live_broker`: live broker abstraction for Alpaca, Interactive Brokers, and Indian broker adapters.
- `strategy`, `risk`, `execution`, `portfolio`, `database`, `backtesting`, `monitoring`, and `api`.

Markets are enabled in `config.yaml`. Future countries can be added by defining market metadata, currency, exchanges, broker key, and watchlist, then implementing the broker adapter if execution is needed.

## Database

SQLAlchemy models cover users, accounts, currencies, markets, brokers, positions, orders, trades, news, signals, portfolio history, exchange rates, strategy logs, backtests, risk events, and audit logs.

## Roadmap

- Real Finnhub, Polygon, Alpha Vantage, and Twelve Data adapters using provider API keys.
- PostgreSQL repositories for provider data, news, indicators, signals, AI analysis, and virtual broker events.
- Real Indian broker adapter.
- Exchange holiday calendars and official market status integrations.
- Persistent order/event logging through repositories.
- Authenticated dashboard frontend.
- Live market-data websockets.
- Broker reconciliation on startup for every enabled market.
- Strategy versioning and walk-forward backtesting.

## Architecture Diagram

```text
Dashboard/API
    |
    v
Signal Engine <---- AI Analysis Service <---- News Service Provider Chain
    |                    ^
    |                    |
    v                    |
Risk Manager <---- Market Data Service Provider Chain + Cache
    |
    v
Execution Engine
    |
    +--> Virtual Broker default for paper trading
    |
    +--> Live Broker adapters only when explicitly enabled
```

## Daily Email Reports

The bot can generate a daily PDF report and email it to `gkkcsp2023@gmail.com`.

The report includes:

- date and weekday
- daily order list
- order status and reason
- profit/loss explanation
- balances by currency
- portfolio value
- US market status
- no-trade explanation when no trades occurred

Configure SMTP in `.env`. For Gmail, use a Google app password, not your normal Gmail password:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_gmail_app_password
SMTP_FROM_EMAIL=your_email@gmail.com
SMTP_USE_TLS=true
DAILY_REPORT_TO=gkkcsp2023@gmail.com
```

Generate and send:

```powershell
python -m trading_bot.app.cli --mode send-daily-report --to gkkcsp2023@gmail.com
```

If SMTP is not configured, the PDF is still created locally under `reports/`.
