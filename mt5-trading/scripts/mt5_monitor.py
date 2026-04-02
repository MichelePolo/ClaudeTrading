#!/usr/bin/env python3
"""
MT5 Monitor — Continuous monitoring with configurable rules.

Features:
  - Monitoring loop with configurable interval
  - Automatic trailing stop on active positions
  - Automatic break-even when profit exceeds a threshold
  - Price level alerts (breakout / breakdown)
  - Automatic close on conditions (max profit, max loss, time)
  - Technical indicator alerts (RSI overbought/oversold, MACD cross)
  - TEMA/price crossover detection with automatic trade execution
  - Logging of all actions to a JSON file
  - Optional desktop notifications (Windows toast)

Usage:
  python mt5_monitor.py config.json
  python mt5_monitor.py --generate-config     # Generate example config
  python mt5_monitor.py config.json --dry-run  # Simulate without executing

Config format — see --generate-config for a complete example.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
import mt5_trading as mt5t

try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERROR: pip install MetaTrader5", file=sys.stderr)
    sys.exit(1)

# Try to import indicators (optional)
try:
    import mt5_indicators as indicators
    HAS_INDICATORS = True
except ImportError:
    HAS_INDICATORS = False


# ──────────────────────────────────────────────
#  Logging
# ──────────────────────────────────────────────

class MonitorLog:
    """Writes logs in JSON and to console."""

    def __init__(self, log_file: str = "mt5_monitor_log.json"):
        self.log_file = log_file
        self.entries: list[dict] = []

    def log(self, level: str, message: str, data: Optional[dict] = None):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
        }
        if data:
            entry["data"] = data

        self.entries.append(entry)

        # Console
        icon = {"INFO": "ℹ️", "WARN": "⚠️", "ACTION": "🔧", "ALERT": "🔔", "ERROR": "❌"}.get(level, "•")
        print(f"  {icon} [{level}] {message}")

        # Append to file
        try:
            with open(self.log_file, "w", encoding="utf-8") as f:
                json.dump(self.entries[-100:], f, indent=2, ensure_ascii=False, default=str)
        except Exception:
            pass


# ──────────────────────────────────────────────
#  Desktop notifications (Windows)
# ──────────────────────────────────────────────

def _notify_desktop(title: str, message: str):
    """Shows a desktop notification on Windows (best-effort)."""
    try:
        from ctypes import windll
        # Use PowerShell for toast notification
        ps_cmd = (
            f'powershell -Command "New-BurntToastNotification '
            f"-Text '{title}', '{message}'\" 2>nul"
        )
        os.system(ps_cmd)
    except Exception:
        pass  # Not critical


# ──────────────────────────────────────────────
#  Monitoring rules
# ──────────────────────────────────────────────

class MonitorEngine:
    """Monitoring engine that evaluates rules on each cycle."""

    def __init__(self, config: dict, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.log = MonitorLog(config.get("log_file", "mt5_monitor_log.json"))
        self.running = True
        self.cycle_count = 0
        self.alerts_fired: set[str] = set()  # Avoid repeated alerts

    def run(self):
        """Main monitoring loop."""
        interval = self.config.get("interval_seconds", 30)
        max_cycles = self.config.get("max_cycles", 0)  # 0 = infinite

        self.log.log("INFO", f"Monitor started (interval: {interval}s, dry_run: {self.dry_run})")

        # Register signal handler for graceful exit
        signal.signal(signal.SIGINT, self._handle_stop)
        signal.signal(signal.SIGTERM, self._handle_stop)

        while self.running:
            self.cycle_count += 1
            print(f"\n{'='*50}")
            print(f"  Cycle #{self.cycle_count} — {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*50}")

            try:
                self._run_cycle()
            except Exception as e:
                self.log.log("ERROR", f"Error in cycle: {e}")

            if max_cycles > 0 and self.cycle_count >= max_cycles:
                self.log.log("INFO", f"Reached max_cycles ({max_cycles}). Stopping.")
                break

            if self.running:
                time.sleep(interval)

        self.log.log("INFO", "Monitor stopped.")

    def _handle_stop(self, signum, frame):
        self.log.log("INFO", "Stop signal received. Exiting...")
        self.running = False

    def _run_cycle(self):
        """Executes a single monitoring cycle."""
        positions = mt5t.get_positions()
        self.log.log("INFO", f"Open positions: {len(positions)}")

        rules = self.config.get("rules", [])

        for rule in rules:
            if not rule.get("enabled", True):
                continue
            try:
                self._evaluate_rule(rule, positions)
            except Exception as e:
                self.log.log("ERROR", f"Error in rule '{rule.get('name', '?')}': {e}")

    def _evaluate_rule(self, rule: dict, positions: list[dict]):
        """Evaluates a single rule."""
        rule_type = rule.get("type", "")

        if rule_type == "trailing_stop":
            self._rule_trailing_stop(rule, positions)
        elif rule_type == "breakeven":
            self._rule_breakeven(rule, positions)
        elif rule_type == "price_alert":
            self._rule_price_alert(rule)
        elif rule_type == "close_on_profit":
            self._rule_close_on_profit(rule, positions)
        elif rule_type == "close_on_loss":
            self._rule_close_on_loss(rule, positions)
        elif rule_type == "close_on_time":
            self._rule_close_on_time(rule, positions)
        elif rule_type == "indicator_alert":
            self._rule_indicator_alert(rule)
        elif rule_type == "max_drawdown":
            self._rule_max_drawdown(rule, positions)
        elif rule_type == "tema_price_cross":
            self._rule_tema_price_cross(rule)
        else:
            self.log.log("WARN", f"Unknown rule type: {rule_type}")

    # — Automatic Trailing Stop —
    def _rule_trailing_stop(self, rule: dict, positions: list[dict]):
        trail_points = rule["trail_points"]
        symbol_filter = rule.get("symbol")
        magic_filter = rule.get("magic")

        for pos in positions:
            if symbol_filter and pos["symbol"] != symbol_filter:
                continue
            if magic_filter is not None and pos["magic"] != magic_filter:
                continue
            if pos["profit"] <= 0:
                continue  # Only positions in profit

            self.log.log("ACTION", f"Trailing stop on #{pos['ticket']} ({pos['symbol']}): {trail_points} points")
            if not self.dry_run:
                result = mt5t.apply_trailing_stop(pos["ticket"], trail_points)
                self.log.log("INFO", f"  → {result.get('status', 'unknown')}", result)

    # — Automatic Break-even —
    def _rule_breakeven(self, rule: dict, positions: list[dict]):
        min_profit_points = rule.get("min_profit_points", 100)
        offset = rule.get("offset_points", 5)
        symbol_filter = rule.get("symbol")

        for pos in positions:
            if symbol_filter and pos["symbol"] != symbol_filter:
                continue
            # Check that the profit in points is sufficient
            info = mt5.symbol_info(pos["symbol"])
            if not info:
                continue
            point = info.point

            if pos["type"] == "BUY":
                profit_points = (pos["price_current"] - pos["price_open"]) / point
                be_triggered = profit_points >= min_profit_points and pos["sl"] < pos["price_open"]
            else:
                profit_points = (pos["price_open"] - pos["price_current"]) / point
                be_triggered = profit_points >= min_profit_points and (pos["sl"] == 0 or pos["sl"] > pos["price_open"])

            if be_triggered:
                self.log.log("ACTION",
                    f"Break-even on #{pos['ticket']} ({pos['symbol']}): profit {profit_points:.0f} pt > {min_profit_points} pt")
                if not self.dry_run:
                    result = mt5t.move_to_breakeven(pos["ticket"], offset_points=offset)
                    self.log.log("INFO", f"  → {result.get('status', 'unknown')}", result)

    # — Price alert —
    def _rule_price_alert(self, rule: dict):
        symbol = rule["symbol"]
        alert_id = f"price_{symbol}_{rule.get('level', '')}_{rule.get('direction', '')}"
        if alert_id in self.alerts_fired:
            return  # Already notified

        tick = mt5t.get_tick(symbol)
        price = tick["bid"]
        level = rule["level"]
        direction = rule.get("direction", "above")  # "above" or "below"

        triggered = (direction == "above" and price >= level) or \
                    (direction == "below" and price <= level)

        if triggered:
            msg = f"ALERT: {symbol} has {'broken above' if direction == 'above' else 'broken below'} {level} (current: {price})"
            self.log.log("ALERT", msg)
            self.alerts_fired.add(alert_id)
            if rule.get("notify_desktop", False):
                _notify_desktop("MT5 Price Alert", msg)

            # Optional action
            if "action" in rule:
                self.log.log("ACTION", f"Executing action on alert: {rule['action']}")
                if not self.dry_run:
                    from mt5_strategy_executor import execute_action
                    result = execute_action(rule["action"])
                    self.log.log("INFO", f"  → Action result", result)

    # — Close on profit —
    def _rule_close_on_profit(self, rule: dict, positions: list[dict]):
        target_profit = rule["target_profit"]  # In account currency
        symbol_filter = rule.get("symbol")
        magic_filter = rule.get("magic")

        for pos in positions:
            if symbol_filter and pos["symbol"] != symbol_filter:
                continue
            if magic_filter is not None and pos["magic"] != magic_filter:
                continue

            if pos["profit"] >= target_profit:
                self.log.log("ACTION",
                    f"Closing on profit #{pos['ticket']}: {pos['profit']:.2f} >= {target_profit}")
                if not self.dry_run:
                    result = mt5t.close_position(pos["ticket"])
                    self.log.log("INFO", f"  → {result.get('status', 'unknown')}", result)

    # — Close on loss —
    def _rule_close_on_loss(self, rule: dict, positions: list[dict]):
        max_loss = rule["max_loss"]  # In account currency (positive)
        symbol_filter = rule.get("symbol")

        for pos in positions:
            if symbol_filter and pos["symbol"] != symbol_filter:
                continue

            if pos["profit"] <= -abs(max_loss):
                self.log.log("ACTION",
                    f"Closing on loss #{pos['ticket']}: {pos['profit']:.2f} <= -{max_loss}")
                if not self.dry_run:
                    result = mt5t.close_position(pos["ticket"])
                    self.log.log("INFO", f"  → {result.get('status', 'unknown')}", result)

    # — Close on time —
    def _rule_close_on_time(self, rule: dict, positions: list[dict]):
        close_time = rule["close_after"]  # Format "HH:MM"
        h, m = map(int, close_time.split(":"))
        now = datetime.now()

        if now.hour > h or (now.hour == h and now.minute >= m):
            symbol_filter = rule.get("symbol")
            magic_filter = rule.get("magic")

            for pos in positions:
                if symbol_filter and pos["symbol"] != symbol_filter:
                    continue
                if magic_filter is not None and pos["magic"] != magic_filter:
                    continue

                self.log.log("ACTION",
                    f"Closing on time #{pos['ticket']} ({pos['symbol']}): after {close_time}")
                if not self.dry_run:
                    result = mt5t.close_position(pos["ticket"])
                    self.log.log("INFO", f"  → {result.get('status', 'unknown')}", result)

    # — Indicator alerts —
    def _rule_indicator_alert(self, rule: dict):
        if not HAS_INDICATORS:
            self.log.log("WARN", "mt5_indicators not available for indicator_alert")
            return

        symbol = rule["symbol"]
        timeframe = rule.get("timeframe", "H1")
        indicator = rule["indicator"]  # "rsi", "macd_cross", "bb_breakout"
        alert_id = f"indicator_{symbol}_{indicator}_{self.cycle_count // 10}"

        if alert_id in self.alerts_fired:
            return

        analysis = indicators.get_analysis(symbol, timeframe)

        triggered = False
        msg = ""

        if indicator == "rsi_overbought":
            rsi_val = analysis["indicators"]["rsi_14"]
            threshold = rule.get("threshold", 70)
            if rsi_val and rsi_val > threshold:
                triggered = True
                msg = f"RSI overbought on {symbol}: {rsi_val:.1f} > {threshold}"

        elif indicator == "rsi_oversold":
            rsi_val = analysis["indicators"]["rsi_14"]
            threshold = rule.get("threshold", 30)
            if rsi_val and rsi_val < threshold:
                triggered = True
                msg = f"RSI oversold on {symbol}: {rsi_val:.1f} < {threshold}"

        elif indicator == "macd_bullish_cross":
            hist = analysis["indicators"]["macd_histogram"]
            if hist and hist > 0:
                triggered = True
                msg = f"MACD bullish cross on {symbol}: histogram = {hist:.6f}"

        elif indicator == "macd_bearish_cross":
            hist = analysis["indicators"]["macd_histogram"]
            if hist and hist < 0:
                triggered = True
                msg = f"MACD bearish cross on {symbol}: histogram = {hist:.6f}"

        elif indicator == "bb_upper_breakout":
            price = analysis["current_price"]
            bb_upper = analysis["indicators"]["bb_upper"]
            if bb_upper and price > bb_upper:
                triggered = True
                msg = f"Bollinger upper breakout on {symbol}: {price} > {bb_upper}"

        elif indicator == "bb_lower_breakout":
            price = analysis["current_price"]
            bb_lower = analysis["indicators"]["bb_lower"]
            if bb_lower and price < bb_lower:
                triggered = True
                msg = f"Bollinger lower breakout on {symbol}: {price} < {bb_lower}"

        if triggered:
            self.log.log("ALERT", msg)
            self.alerts_fired.add(alert_id)
            if rule.get("notify_desktop", False):
                _notify_desktop("MT5 Indicator Alert", msg)
            if "action" in rule:
                self.log.log("ACTION", f"Executing action: {rule['action']}")
                if not self.dry_run:
                    from mt5_strategy_executor import execute_action
                    result = execute_action(rule["action"])
                    self.log.log("INFO", f"  → Result", result)

    # — TEMA / Price crossover —
    def _rule_tema_price_cross(self, rule: dict):
        """Opens a trade whenever the TEMA crosses the price line.

        Config keys:
          symbol        – e.g. "EURUSD"
          timeframe     – default "H1"
          tema_period   – TEMA period, default 20
          volume        – lot size, default 0.01
          sl_points     – stop-loss in points, default 0 (no SL)
          tp_points     – take-profit in points, default 0 (no TP)
          magic         – magic number, default 0
          close_opposite – if true, close existing opposite position before opening, default true
          comment       – order comment
        """
        if not HAS_INDICATORS:
            self.log.log("WARN", "mt5_indicators not available for tema_price_cross")
            return

        symbol = rule["symbol"]
        timeframe = rule.get("timeframe", "H1")
        period = rule.get("tema_period", 20)
        volume = rule.get("volume", 0.01)
        sl_points = rule.get("sl_points", 0)
        tp_points = rule.get("tp_points", 0)
        magic = rule.get("magic", 0)
        comment = rule.get("comment", "tema_cross")
        close_opposite = rule.get("close_opposite", True)

        # Need at least 2 bars to detect a crossover
        count = max(period * 3 + 10, 100)
        bars = mt5t.get_ohlc(symbol, timeframe, count)
        if len(bars) < 2:
            self.log.log("WARN", f"tema_price_cross: not enough bars for {symbol}")
            return

        closes = [b["close"] for b in bars]
        tema_values = indicators.tema(closes, period)

        # Use the last two closed bars for crossover detection
        prev_close = closes[-2]
        curr_close = closes[-1]
        prev_tema = tema_values[-2]
        curr_tema = tema_values[-1]

        if prev_tema is None or curr_tema is None:
            self.log.log("WARN", f"tema_price_cross: insufficient TEMA data for {symbol}")
            return

        bullish_cross = prev_close <= prev_tema and curr_close > curr_tema
        bearish_cross = prev_close >= prev_tema and curr_close < curr_tema

        if not bullish_cross and not bearish_cross:
            return  # No crossover this cycle

        direction = "BUY" if bullish_cross else "SELL"
        cross_type = "bullish" if bullish_cross else "bearish"
        self.log.log(
            "ALERT",
            f"TEMA cross ({cross_type}) on {symbol} {timeframe}: "
            f"price={curr_close:.5f} TEMA({period})={curr_tema:.5f} → {direction}",
        )

        if self.dry_run:
            return

        # Optionally close the opposite position
        if close_opposite:
            opposite = "SELL" if direction == "BUY" else "BUY"
            positions = mt5t.get_positions(symbol=symbol)
            for pos in positions:
                if pos.get("type") == opposite and (magic == 0 or pos.get("magic") == magic):
                    result = mt5t.close_position(pos["ticket"])
                    self.log.log("ACTION", f"Closed opposite {opposite} #{pos['ticket']}: {result.get('status')}")

        # Calculate SL / TP prices
        tick = mt5t.get_tick(symbol)
        info = mt5t.symbol_info(symbol)
        point = info.get("point", 0.00001)

        if direction == "BUY":
            price = tick["ask"]
            sl = round(price - sl_points * point, info.get("digits", 5)) if sl_points else 0
            tp = round(price + tp_points * point, info.get("digits", 5)) if tp_points else 0
        else:
            price = tick["bid"]
            sl = round(price + sl_points * point, info.get("digits", 5)) if sl_points else 0
            tp = round(price - tp_points * point, info.get("digits", 5)) if tp_points else 0

        result = mt5t.open_market_order(
            symbol=symbol,
            direction=direction,
            volume=volume,
            sl=sl,
            tp=tp,
            magic=magic,
            comment=comment,
        )
        self.log.log("ACTION", f"Opened {direction} {symbol} vol={volume}: {result.get('status', 'unknown')}", result)

    # — Max Drawdown —
    def _rule_max_drawdown(self, rule: dict, positions: list[dict]):
        max_dd_percent = rule["max_drawdown_percent"]
        acc = mt5.account_info()
        if not acc:
            return

        dd = ((acc.balance - acc.equity) / acc.balance) * 100 if acc.balance > 0 else 0

        if dd >= max_dd_percent:
            msg = f"CRITICAL DRAWDOWN: {dd:.2f}% >= {max_dd_percent}%"
            self.log.log("ALERT", msg)
            if rule.get("close_all", False):
                self.log.log("ACTION", "Closing ALL positions due to max drawdown!")
                if not self.dry_run:
                    result = mt5t.close_all_positions()
                    self.log.log("INFO", "Total close result", result)


# ──────────────────────────────────────────────
#  Example config
# ──────────────────────────────────────────────

EXAMPLE_CONFIG = {
    "description": "Example configuration for MT5 Monitor",
    "interval_seconds": 30,
    "max_cycles": 0,
    "log_file": "mt5_monitor_log.json",
    "rules": [
        {
            "name": "Global trailing stop",
            "type": "trailing_stop",
            "enabled": True,
            "trail_points": 200,
            "comment": "Apply 200-point trailing stop to all profitable positions"
        },
        {
            "name": "Break-even EURUSD",
            "type": "breakeven",
            "enabled": True,
            "symbol": "EURUSD",
            "min_profit_points": 150,
            "offset_points": 5,
            "comment": "Move to BE when profit exceeds 15 pips"
        },
        {
            "name": "Breakout alert EURUSD",
            "type": "price_alert",
            "enabled": False,
            "symbol": "EURUSD",
            "level": 1.1000,
            "direction": "above",
            "notify_desktop": True,
            "comment": "Alert if EURUSD breaks above 1.1000"
        },
        {
            "name": "Take profit at 50 EUR",
            "type": "close_on_profit",
            "enabled": False,
            "target_profit": 50.0,
            "comment": "Close positions with profit >= 50 EUR"
        },
        {
            "name": "Stop loss at 30 EUR",
            "type": "close_on_loss",
            "enabled": False,
            "max_loss": 30.0,
            "comment": "Close positions with loss >= 30 EUR"
        },
        {
            "name": "End of day close",
            "type": "close_on_time",
            "enabled": False,
            "close_after": "21:30",
            "comment": "Close everything after 21:30"
        },
        {
            "name": "RSI overbought EURUSD",
            "type": "indicator_alert",
            "enabled": False,
            "symbol": "EURUSD",
            "timeframe": "H1",
            "indicator": "rsi_overbought",
            "threshold": 75,
            "notify_desktop": True,
            "comment": "Alert when RSI > 75"
        },
        {
            "name": "TEMA/Price crossover EURUSD H1",
            "type": "tema_price_cross",
            "enabled": False,
            "symbol": "EURUSD",
            "timeframe": "H1",
            "tema_period": 20,
            "volume": 0.01,
            "sl_points": 200,
            "tp_points": 400,
            "magic": 1001,
            "close_opposite": True,
            "comment": "tema_cross_h1",
            "comment_doc": "BUY when price crosses above TEMA(20), SELL when price crosses below"
        },
        {
            "name": "Max drawdown 5%",
            "type": "max_drawdown",
            "enabled": True,
            "max_drawdown_percent": 5.0,
            "close_all": True,
            "comment": "Close ALL if drawdown exceeds 5%"
        }
    ]
}


# ──────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MT5 Monitor — Continuous monitoring")
    parser.add_argument("config", nargs="?", help="JSON configuration file")
    parser.add_argument("--generate-config", action="store_true", help="Generate example config")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without executing actions")
    parser.add_argument("--interval", type=int, help="Override interval in seconds")
    args = parser.parse_args()

    if args.generate_config:
        out_path = "mt5_monitor_config.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(EXAMPLE_CONFIG, f, indent=2, ensure_ascii=False)
        print(f"Example config saved to: {out_path}")
        sys.exit(0)

    if not args.config:
        parser.print_help()
        sys.exit(1)

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)

    if args.interval:
        config["interval_seconds"] = args.interval

    # Connect to MT5
    print("Connecting to MT5...")
    try:
        info = mt5t.connect()
        print(f"Connected: {info['name']} | Balance: {info['balance']} {info['currency']}\n")
    except Exception as e:
        print(f"Connection error: {e}", file=sys.stderr)
        sys.exit(1)

    # Start monitor
    engine = MonitorEngine(config, dry_run=args.dry_run)
    try:
        engine.run()
    finally:
        mt5t.disconnect()
        print("\nDisconnected from MT5.")


if __name__ == "__main__":
    main()
