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

## XAUUSD.r — MT5 Command Cheatsheet

Quick reference for all CLI commands using XAUUSD.r as the symbol.

### Connessione e account

| Azione | Comando |
|--------|---------|
| Connetti MT5 | `python mt5_trading.py connect` |
| Info account (balance, equity, margin) | `python mt5_trading.py account` |
| Info simbolo XAUUSD.r | `python mt5_trading.py symbol XAUUSD.r` |
| Prezzo corrente bid/ask | `python mt5_trading.py tick XAUUSD.r` |

### Analisi completa — tutti gli indicatori

| Azione | Comando |
|--------|---------|
| Analisi H1 (default, 200 barre) | `python mt5_indicators.py XAUUSD.r --analysis` |
| Analisi M15 — intraday | `python mt5_indicators.py XAUUSD.r --analysis --timeframe M15` |
| Analisi M5 — scalping | `python mt5_indicators.py XAUUSD.r --analysis --timeframe M5` |
| Analisi H4 — swing | `python mt5_indicators.py XAUUSD.r --analysis --timeframe H4` |
| Analisi D1 — visione daily | `python mt5_indicators.py XAUUSD.r --analysis --timeframe D1` |
| Storico esteso (500 barre) | `python mt5_indicators.py XAUUSD.r --analysis --timeframe H1 --count 500` |

### Indicatori specifici

| Azione | Comando |
|--------|---------|
| RSI + MACD + Bollinger + ATR | `python mt5_indicators.py XAUUSD.r --indicators rsi macd bbands atr` |
| Solo RSI (14) | `python mt5_indicators.py XAUUSD.r --indicators rsi` |
| Trend: SMA + EMA + TEMA | `python mt5_indicators.py XAUUSD.r --indicators sma ema tema` |
| Momentum: Stochastic + ADX | `python mt5_indicators.py XAUUSD.r --indicators stoch adx` |
| Volatilità: ATR + Bollinger | `python mt5_indicators.py XAUUSD.r --indicators atr bbands` |
| MACD su M15 — momentum intraday | `python mt5_indicators.py XAUUSD.r --indicators macd --timeframe M15` |
| ADX su D1 — forza trend daily | `python mt5_indicators.py XAUUSD.r --indicators adx --timeframe D1` |

### Pivot points

| Azione | Comando |
|--------|---------|
| Classic (default) | `python mt5_indicators.py XAUUSD.r --pivots classic` |
| Fibonacci | `python mt5_indicators.py XAUUSD.r --pivots fibonacci` |
| Camarilla (intraday) | `python mt5_indicators.py XAUUSD.r --pivots camarilla` |

### OHLC — dati storici grezzi

| Azione | Comando |
|--------|---------|
| Ultime 50 candele H1 | `python mt5_trading.py ohlc XAUUSD.r --timeframe H1 --count 50` |
| Ultime 100 candele D1 | `python mt5_trading.py ohlc XAUUSD.r --timeframe D1 --count 100` |

### Posizioni e ordini aperti

| Azione | Comando |
|--------|---------|
| Posizioni aperte | `python mt5_trading.py positions` |
| Ordini pendenti | `python mt5_trading.py pending` |

### Monitoraggio continuo

| Azione | Comando |
|--------|---------|
| Genera config di esempio | `python mt5_monitor.py --generate-config` |
| Avvia monitor con config | `python mt5_monitor.py mt5_monitor_config.json` |
| Dry-run — simula senza eseguire | `python mt5_monitor.py mt5_monitor_config.json --dry-run` |
| Intervallo custom (ogni 10 sec) | `python mt5_monitor.py mt5_monitor_config.json --interval 10` |

> **Nota:** `Ctrl+C` per fermare il monitor. Log scritto su `mt5_monitor_log.json`.

## License

MIT
