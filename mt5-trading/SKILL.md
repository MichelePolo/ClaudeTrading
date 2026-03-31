---
name: mt5-trading
description: >
  Control MetaTrader 5 directly from Claude: open, close, modify trades, manage pending
  orders, calculate lot sizes, apply trailing stop and break-even. Use this skill EVERY TIME
  the user mentions trading, MetaTrader, MT5, forex, opening/closing positions, stop loss,
  take profit, orders, lots, risk percentage, trailing stop, break-even, or describes a
  trading strategy to execute. Even if the user doesn't explicitly say "MT5", if they talk
  about trading currency pairs, indices, commodities, or describe entry/exit rules for
  the market, this is the right skill.
---

# MT5 Trading Skill

This skill enables Claude to operate as a trading assistant on MetaTrader 5, executing
real operations on the user's account via a local Python library.

## Architecture

```
mt5-trading/
├── SKILL.md                          ← This file (instructions for Claude)
├── scripts/
│   ├── mt5_trading.py                ← Python library + CLI for MT5
│   ├── mt5_strategy_executor.py      ← JSON strategy executor
│   ├── mt5_indicators.py             ← Technical indicators (RSI, MACD, BB, ATR, ADX...)
│   └── mt5_monitor.py                ← Continuous monitoring with automatic rules
└── references/
    ├── strategy_format.md            ← JSON strategy format
    └── monitor_rules.md              ← Monitor rules documentation
```

## Prerequisites (user's PC)

1. **Windows** with MetaTrader 5 installed and running
2. **Python 3.9+** with the `MetaTrader5` package:
   ```
   pip install MetaTrader5
   ```
3. The `mt5_trading.py` and `mt5_strategy_executor.py` files copied to the PC
4. The MT5 terminal must be open and logged into an account (demo or live)

> **IMPORTANT**: These scripts run on the user's PC, NOT in Claude's sandbox.
> Claude generates commands/strategies, the user executes them locally.

## How Claude Should Operate

### Standard Flow

1. **The user describes what they want to do** (in natural language)
2. **Claude translates into commands** using the `mt5_trading.py` library
3. **Claude presents the commands** ready for the user to execute
4. **The user copies and executes** on their own PC

### Two Output Modes

#### Mode A — Single CLI Commands
For simple and direct operations. Claude provides `python mt5_trading.py ...` commands.

Examples:
```bash
# Connect
python mt5_trading.py connect

# View account
python mt5_trading.py account

# Buy 0.1 lots EURUSD with SL and TP
python mt5_trading.py buy EURUSD 0.1 --sl 1.0800 --tp 1.1000 --magic 1001

# Close position
python mt5_trading.py close 123456

# Trailing stop
python mt5_trading.py trailing 123456 200

# Calculate lot for 1% risk with 300-point SL
python mt5_trading.py lot_size EURUSD 1.0 300
```

#### Mode B — JSON Strategy
For complex multi-step operations. Claude generates a JSON and provides the command
to execute it via `mt5_strategy_executor.py`.

```bash
# Save the JSON to a file
# Then execute:
python mt5_strategy_executor.py strategy.json

# Or inline:
python mt5_strategy_executor.py --inline '{ "actions": [...] }'
```

For the complete JSON format, see: `references/strategy_format.md`

## Fundamental Rules for Claude

### Safety and Confirmation

1. **NEVER execute automatically** — Claude generates commands, the user executes
2. **Always ask for confirmation** before generating market orders
3. **Always show a summary** before execution:
   - Symbol, direction, volume
   - Stop loss and take profit (in price AND pips/points)
   - Estimated risk in currency and percentage
4. **Explicitly warn** if SL or TP are missing
5. **Always suggest using a demo account** for testing

### Risk Management

Claude must ALWAYS consider risk:

- If the user doesn't specify volume, **calculate the lot** based on risk
  (default: 1% of balance per trade, unless otherwise specified)
- If the user doesn't specify SL, **always ask** before proceeding
- If risk exceeds 2% per single trade, **warn** explicitly
- Keep track of open positions in the conversation

### Translating the User's Strategy

When the user describes a strategy in natural language, Claude must:

1. **Restate the strategy** in a structured way for confirmation
2. **Identify**: entry conditions, exit conditions, risk management
3. **Translate** into JSON actions or CLI commands
4. **Highlight** any ambiguities or risks
5. **Suggest** improvements (e.g., trailing stop if active management is missing)

### Example Conversation

**User**: "I want to buy EURUSD if it breaks 1.1000, with a 30-pip stop and 60-pip target.
Risk 1% of the account."

**Claude should**:
1. Confirm the strategy:
   - Entry: BUY_STOP at 1.1000
   - SL: 1.0970 (30 pips below)
   - TP: 1.1060 (60 pips above)
   - Risk: 1% of balance
2. First generate the lot calculation:
   ```bash
   python mt5_trading.py lot_size EURUSD 1.0 300
   ```
3. Then the pending order (after getting the lot):
   ```bash
   python mt5_trading.py pending_order EURUSD BUY_STOP [LOT] 1.1000 --sl 1.0970 --tp 1.1060 --magic 1001 --comment "breakout_long"
   ```

## Available CLI Commands (quick reference)

| Command | Description |
|---------|-------------|
| `connect` | Connect to MT5 |
| `disconnect` | Disconnect |
| `account` | Account info (balance, equity, margin) |
| `symbol EURUSD` | Symbol info (spread, digits, volumes) |
| `tick EURUSD` | Latest bid/ask price |
| `ohlc EURUSD --timeframe H1 --count 20` | OHLC candles |
| `positions` | Open positions |
| `pending` | Pending orders |
| `buy EURUSD 0.1 --sl X --tp Y` | Market BUY order |
| `sell EURUSD 0.1 --sl X --tp Y` | Market SELL order |
| `pending_order EURUSD BUY_LIMIT 0.1 1.0850 --sl X --tp Y` | Pending order |
| `close 123456` | Close position (full) |
| `close 123456 --volume 0.05` | Partial close |
| `close_all` | Close all |
| `close_all --symbol EURUSD` | Close all for symbol |
| `cancel 789012` | Cancel pending order |
| `cancel_all` | Cancel all pending |
| `modify 123456 --sl 1.0850 --tp 1.1050` | Modify SL/TP |
| `modify_pending 789012 --price 1.0840` | Modify pending order |
| `trailing 123456 200` | Trailing stop (200 points) |
| `breakeven 123456 --offset 10` | Move SL to break-even |
| `lot_size EURUSD 1.0 300` | Calculate lot (1% risk, 300pt SL) |

Every command outputs the result in JSON. Always prefix with:
```
python mt5_trading.py <command>
```

## When to Use Mode A vs B

- **Mode A (CLI)**: single operations, informational queries, quick modifications
- **Mode B (JSON strategy)**: multi-step strategies, complex setups with multiple orders,
  sequences requiring coordination (e.g., close all → wait → reopen)

## Pip ↔ Point Conversion

- Forex 5 digits (e.g., EURUSD): 1 pip = 10 points. So 30 pips = 300 points
- Forex 3 digits (e.g., USDJPY): 1 pip = 10 points. So 30 pips = 300 points
- Indices/metals: depends on the symbol, Claude should always verify with `symbol_info`
- **IMPORTANT**: the library works in points. Claude must convert if the user speaks in pips.

## Common Errors and Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `MT5 not initialized` | Terminal not started | `python mt5_trading.py connect` |
| `Symbol not found` | Symbol unavailable | Check exact name with broker |
| `Invalid volume` | Lot out of range | Check limits with `symbol_info` |
| `Order rejected [10013]` | Market closed | Check trading hours |
| `Order rejected [10016]` | Invalid SL/TP | SL/TP too close to price |
| `Insufficient margin` | Insufficient funds | Reduce volume or close positions |

## Mode C — Technical Analysis with Indicators

The `mt5_indicators.py` script provides technical indicators calculated directly on MT5 data.
Claude should use it BEFORE suggesting trades, to support decisions with objective data.

### Indicator Commands

```bash
# Full analysis (all indicators + signals + bias)
python mt5_indicators.py EURUSD --analysis

# Specific indicators
python mt5_indicators.py EURUSD --indicators rsi macd bbands atr

# Daily pivot points
python mt5_indicators.py EURUSD --pivots classic
python mt5_indicators.py EURUSD --pivots fibonacci
python mt5_indicators.py EURUSD --pivots camarilla

# Different timeframe
python mt5_indicators.py XAUUSD --analysis --timeframe M15
```

### Available Indicators

| Indicator | CLI Key | Output |
|-----------|---------|--------|
| SMA (20, 50, 200) | `sma` | Simple moving averages |
| EMA (12, 26) | `ema` | Exponential moving averages |
| RSI (14) | `rsi` | Relative strength index (0-100) |
| MACD (12,26,9) | `macd` | Line, signal, histogram |
| Bollinger Bands (20,2) | `bbands` | Upper, middle, lower |
| ATR (14) | `atr` | Average volatility |
| Stochastic (14,3) | `stoch` | %K and %D (0-100) |
| ADX (14) | `adx` | Trend strength + DI+/DI- |
| Pivot Points | `--pivots` | Classic, Fibonacci, Camarilla |

### How Claude Uses Analysis

The `--analysis` output includes an `overall_bias` field (BULLISH / BEARISH / NEUTRAL) and
a `signals` list with each indicator and its signal. Claude should:

1. **Run the analysis** before proposing a trade
2. **Cite the indicators** that support the decision
3. **Warn** if signals are conflicting
4. **Use ATR** to calculate SL/TP proportional to volatility

Example workflow for Claude:
- User: "What do you think about going long on EURUSD?"
- Claude generates: `python mt5_indicators.py EURUSD --analysis`
- Claude reads the JSON and responds: "RSI at 45 (neutral), MACD bullish, price above SMA200.
  Overall bias: moderately bullish. ATR at 80 points, I suggest SL at 120pt and TP at 160pt."

## Mode D — Continuous Monitoring

The `mt5_monitor.py` script runs in a loop on the user's PC and applies automatic rules.
Claude generates the JSON configuration, the user executes it.

### Monitor Commands

```bash
# Generate an example config
python mt5_monitor.py --generate-config

# Start the monitor
python mt5_monitor.py mt5_monitor_config.json

# Simulation mode (doesn't execute real actions)
python mt5_monitor.py mt5_monitor_config.json --dry-run

# Override interval
python mt5_monitor.py mt5_monitor_config.json --interval 10
```

### Available Rule Types

| Type | Description |
|------|-------------|
| `trailing_stop` | Automatic trailing stop on profitable positions |
| `breakeven` | Move SL to break-even when profit exceeds a threshold |
| `price_alert` | Notify when price crosses above/below a level |
| `close_on_profit` | Close position when target profit is reached (currency) |
| `close_on_loss` | Close position when loss exceeds a limit (currency) |
| `close_on_time` | Close positions after a specified time (HH:MM) |
| `indicator_alert` | Alerts based on indicators (RSI, MACD cross, Bollinger breakout) |
| `max_drawdown` | Close ALL if account drawdown exceeds a percentage |

### How Claude Generates Monitor Configurations

When the user describes automatic management rules, Claude should:

1. **Translate** the rules into the monitor JSON format
2. **Suggest `--dry-run`** for the first test
3. **Always include** the `max_drawdown` rule as protection
4. **Explain** what each rule will do

Example:
- User: "I want my positions protected automatically:
  trailing stop at 20 pips, break-even after 15 pips of profit,
  and close everything if I lose more than 3%"
- Claude generates a JSON config with 3 rules and saves it as a file

### Monitor Config Structure

```json
{
  "interval_seconds": 30,
  "log_file": "mt5_monitor_log.json",
  "rules": [
    {
      "name": "Descriptive name",
      "type": "trailing_stop",
      "enabled": true,
      "trail_points": 200,
      "symbol": "EURUSD"
    }
  ]
}
```

For the complete rules documentation, see: `references/monitor_rules.md`

### Alerts with Automatic Actions

The `price_alert` and `indicator_alert` rules can include an action to execute
automatically when the alert triggers:

```json
{
  "type": "price_alert",
  "symbol": "EURUSD",
  "level": 1.1000,
  "direction": "above",
  "notify_desktop": true,
  "action": {
    "action": "buy",
    "symbol": "EURUSD",
    "volume": 0.1,
    "sl": 1.0970,
    "tp": 1.1060
  }
}
```

## Complete Decision Flow for Claude

When the user asks for a trade or strategy, Claude follows this flow:

1. **Analysis** → `python mt5_indicators.py SYMBOL --analysis`
2. **Account** → `python mt5_trading.py account` (for balance and margin)
3. **Lot calculation** → `python mt5_trading.py lot_size SYMBOL RISK SL_POINTS`
4. **Summary** → Present to user: indicators, direction, volume, SL, TP, risk
5. **Confirmation** → Wait for user OK
6. **Execution** → Generate the command/strategy
7. **Monitoring** → Suggest monitor config if automatic rules are needed

## Important Notes

- Outputs are **always in JSON** for easy parsing
- The **magic number** identifies the strategy (useful for managing multiple strategies)
- Claude should suggest different magic numbers for different strategies
- If the user asks for OHLC or tick data, Claude analyzes them to support decisions
- The monitor writes a log to `mt5_monitor_log.json` that can be checked at any time
- Press `Ctrl+C` to stop the monitor cleanly
