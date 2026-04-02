# ClaudeTrading

## Project Overview

This is a Claude Code skill (`mt5-trading`) that enables Claude to act as a MetaTrader 5 trading assistant. Claude generates CLI commands and JSON strategies; the user executes them locally on their Windows PC.

## Documentation Rule

**MANDATORY**: When adding, modifying, or removing features, indicators, monitor rules, or CLI commands, you MUST update ALL related documentation and code comments in the same change. This includes:
- `CLAUDE.md` — File Structure, Decision Flow, and any relevant sections
- `mt5-trading/SKILL.md` — Architecture tree, indicator/rule tables, CLI reference, examples
- `README.md` — Feature list, command tables, monitor rules table
- `mt5-trading/references/monitor_rules.md` — Rule docs (if monitor rules are affected)
- Code docstrings in the affected scripts (indicator lists, feature lists, CLI usage examples)

Never ship code changes without the corresponding doc updates. If in doubt, grep for the old name/feature across all `.md` files and all script docstrings to ensure nothing is missed.

## Key Constraints

- **Claude NEVER auto-executes trades** — always generate commands for the user to run
- **Always ask for confirmation** before generating market orders
- **Always show a risk summary** (symbol, direction, volume, SL, TP, risk %)
- **Warn if SL is missing** or risk exceeds 2% per trade
- **Default risk**: 1% of balance per trade unless user specifies otherwise
- The scripts require Windows + MetaTrader 5 + `pip install MetaTrader5`

## Decision Flow

When the user asks for a trade:
1. Run technical analysis (`mt5_indicators.py --analysis`)
2. Check account info (`mt5_trading.py account`)
3. Calculate lot size (`mt5_trading.py lot_size`)
4. Present summary and ask for confirmation
5. Generate the execution command
6. Optionally suggest monitoring rules

## Pip/Point Conversion

- Forex 5 digits (EURUSD, GBPUSD): 1 pip = 10 points
- Forex 3 digits (USDJPY): 1 pip = 10 points
- Metals/indices: varies by symbol — always verify with `symbol_info`

## File Structure

- `mt5-trading/SKILL.md` — Main skill instructions
- `mt5-trading/scripts/mt5_trading.py` — Core trading library + CLI
- `mt5-trading/scripts/mt5_strategy_executor.py` — JSON strategy runner
- `mt5-trading/scripts/mt5_indicators.py` — Technical indicators
- `mt5-trading/scripts/mt5_monitor.py` — Position monitoring
- `mt5-trading/references/strategy_format.md` — JSON strategy schema
- `mt5-trading/references/monitor_rules.md` — Monitor rules docs
