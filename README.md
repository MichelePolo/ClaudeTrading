# ClaudeTrading

A Claude Code skill that turns Claude into a MetaTrader 5 trading assistant. Claude generates commands and strategies — you execute them on your PC.

## What It Does

Claude can:
- **Open/close trades** — market orders, pending orders, partial closes
- **Manage risk** — auto-calculate lot size from risk %, enforce SL/TP
- **Analyze markets** — RSI, MACD, Bollinger Bands, ATR, ADX, Stochastic, TEMA, Pivot Points
- **Build strategies** — multi-step JSON strategies executed sequentially
- **Monitor positions** — trailing stop, break-even, price alerts, drawdown protection

## Architecture

```
mt5-trading/
├── SKILL.md                        # Skill instructions for Claude
├── scripts/
│   ├── mt5_trading.py              # Core library + CLI for MT5
│   ├── mt5_strategy_executor.py    # Executes JSON strategies
│   ├── mt5_indicators.py           # Technical indicators
│   └── mt5_monitor.py              # Continuous monitoring with rules
└── references/
    ├── strategy_format.md          # JSON strategy format docs
    └── monitor_rules.md            # Monitor rules documentation
```

## Prerequisites

1. **Windows** with MetaTrader 5 installed and running
2. **Python 3.9+** with the `MetaTrader5` package:
   ```
   pip install MetaTrader5
   ```
3. MT5 terminal open and logged into an account (demo or live)

## Quick Start

```bash
# Connect to MT5
python mt5_trading.py connect

# Check account info
python mt5_trading.py account

# Get technical analysis
python mt5_indicators.py EURUSD --analysis

# Calculate lot size for 1% risk with 300-point SL
python mt5_trading.py lot_size EURUSD 1.0 300

# Buy 0.1 lots EURUSD with SL and TP
python mt5_trading.py buy EURUSD 0.1 --sl 1.0800 --tp 1.1000

# Start position monitor (dry-run first)
python mt5_monitor.py config.json --dry-run
```

## How It Works

1. You describe what you want in natural language
2. Claude translates your request into commands or JSON strategies
3. Claude shows a summary with risk details and asks for confirmation
4. You copy and execute the commands on your PC

**Claude never executes trades automatically** — you always have final control.

## Four Modes

| Mode | Use Case | Tool |
|------|----------|------|
| **A — CLI Commands** | Single operations, quick queries | `mt5_trading.py` |
| **B — JSON Strategy** | Multi-step operations, complex setups | `mt5_strategy_executor.py` |
| **C — Technical Analysis** | Indicators, signals, market bias | `mt5_indicators.py` |
| **D — Monitoring** | Automated trailing, alerts, drawdown protection | `mt5_monitor.py` |

## Risk Management

- Default risk: 1% per trade (configurable)
- Claude always asks if SL is missing
- Warns if risk exceeds 2% per trade
- Pip-to-point conversion handled automatically (Forex 5-digit: 1 pip = 10 points)
- For metals/indices, Claude verifies conversion via `symbol_info`

## Available CLI Commands

| Command | Description |
|---------|-------------|
| `connect` | Connect to MT5 |
| `account` | Account info (balance, equity, margin) |
| `symbol EURUSD` | Symbol info (spread, digits, volumes) |
| `tick EURUSD` | Latest bid/ask price |
| `ohlc EURUSD --timeframe H1` | OHLC candles |
| `positions` | Open positions |
| `pending` | Pending orders |
| `buy/sell SYMBOL VOL --sl X --tp Y` | Market order |
| `pending_order SYMBOL TYPE VOL PRICE` | Pending order |
| `close TICKET` | Close position |
| `close_all` | Close all positions |
| `modify TICKET --sl X --tp Y` | Modify SL/TP |
| `trailing TICKET POINTS` | Trailing stop |
| `breakeven TICKET` | Move SL to break-even |
| `lot_size SYMBOL RISK% SL_POINTS` | Calculate lot from risk |

## Monitor Rules

| Rule Type | Description |
|-----------|-------------|
| `trailing_stop` | Auto trailing stop on profitable positions |
| `breakeven` | Move SL to break-even after profit threshold |
| `price_alert` | Alert (+ optional action) on price levels |
| `close_on_profit` | Close at profit target (account currency) |
| `close_on_loss` | Close at max loss (account currency) |
| `close_on_time` | Close after specified time (HH:MM) |
| `indicator_alert` | Alert on RSI, MACD cross, Bollinger breakout |
| `tema_price_cross` | Open trade on TEMA/price crossover |
| `max_drawdown` | Close ALL if account drawdown exceeds threshold |

## License

MIT
