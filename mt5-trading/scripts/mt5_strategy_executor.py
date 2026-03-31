#!/usr/bin/env python3
"""
MT5 Strategy Executor — Executes strategies defined in JSON.

This script is the bridge between Claude (which generates strategies in JSON)
and the mt5_trading.py library that executes them on MetaTrader 5.

Usage:
    python mt5_strategy_executor.py strategy.json
    python mt5_strategy_executor.py --inline '{"actions": [...]}'
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add the current directory to the path to import mt5_trading
sys.path.insert(0, str(Path(__file__).parent))
import mt5_trading as mt5t


def execute_action(action: dict) -> dict:
    """Execute a single trading action.

    Args:
        action: dict with key "action" and specific parameters.

    Returns:
        dict with result.
    """
    act = action.get("action", "").lower()
    params = {k: v for k, v in action.items() if k != "action"}

    action_map = {
        "connect": mt5t.connect,
        "disconnect": mt5t.disconnect,
        "account_info": lambda **_: mt5t.account_info(),
        "symbol_info": lambda **p: mt5t.symbol_info(p["symbol"]),
        "get_tick": lambda **p: mt5t.get_tick(p["symbol"]),
        "get_ohlc": lambda **p: mt5t.get_ohlc(
            p["symbol"], p.get("timeframe", "H1"), p.get("count", 100)
        ),
        "get_positions": lambda **p: mt5t.get_positions(
            symbol=p.get("symbol"), magic=p.get("magic")
        ),
        "get_pending_orders": lambda **p: mt5t.get_pending_orders(
            symbol=p.get("symbol")
        ),
        "buy": lambda **p: mt5t.open_market_order(
            symbol=p["symbol"], direction="BUY",
            volume=p["volume"], sl=p.get("sl", 0), tp=p.get("tp", 0),
            magic=p.get("magic", 0), comment=p.get("comment", ""),
        ),
        "sell": lambda **p: mt5t.open_market_order(
            symbol=p["symbol"], direction="SELL",
            volume=p["volume"], sl=p.get("sl", 0), tp=p.get("tp", 0),
            magic=p.get("magic", 0), comment=p.get("comment", ""),
        ),
        "pending_order": lambda **p: mt5t.open_pending_order(
            symbol=p["symbol"], order_type=p["order_type"],
            volume=p["volume"], price=p["price"],
            sl=p.get("sl", 0), tp=p.get("tp", 0),
            magic=p.get("magic", 0), comment=p.get("comment", ""),
        ),
        "close": lambda **p: mt5t.close_position(
            ticket=p["ticket"], volume=p.get("volume"),
        ),
        "close_all": lambda **p: mt5t.close_all_positions(
            symbol=p.get("symbol"), magic=p.get("magic"),
        ),
        "cancel": lambda **p: mt5t.cancel_pending_order(p["ticket"]),
        "cancel_all": lambda **p: mt5t.cancel_all_pending_orders(
            symbol=p.get("symbol"),
        ),
        "modify": lambda **p: mt5t.modify_position(
            ticket=p["ticket"], sl=p.get("sl"), tp=p.get("tp"),
        ),
        "modify_pending": lambda **p: mt5t.modify_pending_order(
            ticket=p["ticket"], price=p.get("price"),
            sl=p.get("sl"), tp=p.get("tp"),
        ),
        "trailing_stop": lambda **p: mt5t.apply_trailing_stop(
            ticket=p["ticket"], trail_points=p["trail_points"],
        ),
        "breakeven": lambda **p: mt5t.move_to_breakeven(
            ticket=p["ticket"], offset_points=p.get("offset_points", 0),
        ),
        "calculate_lot": lambda **p: mt5t.calculate_lot_size(
            symbol=p["symbol"], risk_percent=p["risk_percent"],
            sl_points=p["sl_points"],
        ),
        "wait": lambda **p: _wait(p.get("seconds", 1)),
    }

    if act not in action_map:
        return {"error": f"Unknown action: '{act}'", "available": list(action_map.keys())}

    try:
        return action_map[act](**params)
    except Exception as e:
        return {"error": str(e), "action": act}


def _wait(seconds: float) -> dict:
    time.sleep(seconds)
    return {"status": "waited", "seconds": seconds}


def execute_strategy(strategy: dict) -> list[dict]:
    """Execute a list of actions sequentially.

    Args:
        strategy: dict with key "actions" (list of actions).
            Optional: "description", "risk_rules".

    Returns:
        List of results for each action.
    """
    actions = strategy.get("actions", [])
    results = []

    print(f"=== Strategy: {strategy.get('description', 'N/A')} ===")
    print(f"=== Actions to execute: {len(actions)} ===\n")

    for i, action in enumerate(actions, 1):
        print(f"[{i}/{len(actions)}] Executing: {action.get('action', '?')} ...", end=" ")
        result = execute_action(action)
        results.append({"action_index": i, "action": action, "result": result})

        if "error" in result:
            print(f"ERROR: {result['error']}")
            # If the action has stop_on_error, stop execution
            if action.get("stop_on_error", False):
                print(">>> Stop on error is active. Stopping the strategy.")
                break
        else:
            print("OK")

    print(f"\n=== Strategy completed: {len(results)} actions executed ===")
    return results


def main():
    parser = argparse.ArgumentParser(description="Execute MT5 strategy from JSON file")
    parser.add_argument("file", nargs="?", help="JSON file of the strategy")
    parser.add_argument("--inline", help="Inline JSON of the strategy")
    args = parser.parse_args()

    if args.inline:
        strategy = json.loads(args.inline)
    elif args.file:
        with open(args.file) as f:
            strategy = json.load(f)
    else:
        parser.print_help()
        sys.exit(1)

    results = execute_strategy(strategy)
    print("\n" + json.dumps(results, indent=2, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
