# Stock Trading Bot Version 1

Paper-first Python trading bot with Alpaca paper trading support, technical filters, news sentiment, risk controls, SQLite logging, and a simple backtester.

This is not a guaranteed-profit system. It is a safe, testable starting point for research and paper trading.

## Safety Defaults

- Default broker mode is `paper`.
- Version 1 refuses live trading in `AlpacaBrokerClient`.
- API keys are read from environment variables only.
- `ALLOW_LIVE_TRADING=false` by default.
- `EMERGENCY_STOP=true` disables new buys.
- Missing market data, missing news, or low-confidence sentiment causes a skip.
- Every buy, sell, hold, and skip decision is logged.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with Alpaca paper credentials:

```powershell
$env:ALPACA_API_KEY="your_paper_key"
$env:ALPACA_SECRET_KEY="your_paper_secret"
$env:ALLOW_LIVE_TRADING="false"
$env:EMERGENCY_STOP="false"
```

## Configuration

Edit `stock_trading_bot/config.yaml`:

- `watchlist`: symbols to analyze.
- `risk.risk_per_trade_pct`: max account value risked per trade, default `0.01`.
- `risk.max_open_positions`: portfolio concentration control.
- `risk.max_daily_loss_pct`: stops new trades after daily account loss.
- `strategy.sentiment_buy_threshold`: minimum news score to consider a buy.
- `strategy.sentiment_sell_threshold`: strongly negative news exit threshold.

## Example Paper Run Without Alpaca Credentials

This uses mock market/news data and a mock broker. It still writes orders to SQLite and logs decisions.

```powershell
python main.py --mode example
```

Example output:

```text
INFO paper_cycle - Starting paper cycle. equity=100000.00 watchlist=AAPL,MSFT,NVDA,TSLA,AMZN,META,GOOGL
INFO stock_trading_bot.execution.order_manager - BUY AAPL x6 @ 161.60 (filled)
INFO stock_trading_bot.execution.order_manager - BUY MSFT x5 @ 189.60 (filled)
INFO stock_trading_bot.execution.order_manager - BUY NVDA x5 @ 172.60 (filled)
INFO paper_cycle - META skipped by risk manager: Max open positions reached
INFO paper_cycle - Paper cycle complete. open_positions=['AAPL', 'MSFT', 'NVDA', 'TSLA', 'AMZN']
```

Actual values may differ because mock prices are generated per symbol.

## Alpaca Paper Trading

Run only after setting paper credentials:

```powershell
python main.py --mode paper
```

Version 1 submits market orders only to Alpaca paper trading. Do not change broker mode to `live`; the Alpaca client will reject it.

## Backtesting

Run the built-in sample:

```powershell
python main.py --mode backtest
```

Run with a CSV:

```powershell
python main.py --mode backtest --csv path\to\history.csv
```

CSV must include at least:

```csv
close,volume
100,1000000
101,1200000
```

Backtest reports total return, win rate, average win, average loss, max drawdown, number of trades, best trade, and worst trade.

## How It Works

1. Market data calculates current price, daily change, volume, average volume, moving averages, RSI, and trend.
2. News headlines are scored from `-100` to `+100` and labeled from very negative to very positive.
3. Buy logic requires positive news, positive trend, above-average volume, RSI below the overbought limit, no existing position, and risk approval.
4. Sell logic exits on 10% loss, strongly negative news, profit-lock hit, or risk-manager exposure exit.
5. Profit lock starts at `-10%` and only moves upward:
   - `+10%` profit locks `+3%`
   - `+20%` locks `+10%`
   - `+30%` locks `+18%`
   - `+50%` locks `+35%`
   - `+75%` locks `+55%`
   - `+100%` locks `+80%`
6. SQLite stores orders, reasons, prices, sentiment score, indicators, P/L, timestamp, and stop/profit-lock level.

## Tests

```powershell
pytest
```

## Version 2 Ideas

- Persistent position reconciliation from Alpaca on startup.
- Better backtesting with realistic fills, slippage, commissions, corporate actions, and survivorship-bias-free data.
- Multiple sentiment providers with source weighting and duplicate headline filtering.
- Intraday bars and scheduled execution windows.
- Portfolio-level beta/sector exposure limits.
- Alerting through email, Slack, or SMS.
- Human approval mode before paper orders.
- Rich dashboard for positions, risk, and trade history.
