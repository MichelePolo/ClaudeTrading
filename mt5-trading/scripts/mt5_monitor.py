#!/usr/bin/env python3
"""
MT5 Monitor — Monitoraggio continuo con regole configurabili.

Funzionalità:
  - Loop di monitoraggio con intervallo configurabile
  - Trailing stop automatico su posizioni attive
  - Break-even automatico quando il profitto supera una soglia
  - Alert su livelli di prezzo (breakout / breakdown)
  - Chiusura automatica su condizioni (max profit, max loss, orario)
  - Alert su indicatori tecnici (RSI overbought/oversold, MACD cross)
  - Log di tutte le azioni in un file JSON
  - Notifiche desktop (Windows toast) opzionali

Uso:
  python mt5_monitor.py config.json
  python mt5_monitor.py --generate-config     # Genera config di esempio
  python mt5_monitor.py config.json --dry-run  # Simula senza eseguire

Formato config — vedi --generate-config per un esempio completo.
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

# Prova a importare gli indicatori (opzionale)
try:
    import mt5_indicators as indicators
    HAS_INDICATORS = True
except ImportError:
    HAS_INDICATORS = False


# ──────────────────────────────────────────────
#  Logging
# ──────────────────────────────────────────────

class MonitorLog:
    """Scrive log in JSON e su console."""

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
#  Notifiche desktop (Windows)
# ──────────────────────────────────────────────

def _notify_desktop(title: str, message: str):
    """Mostra una notifica desktop su Windows (best-effort)."""
    try:
        from ctypes import windll
        # Usa PowerShell per toast notification
        ps_cmd = (
            f'powershell -Command "New-BurntToastNotification '
            f"-Text '{title}', '{message}'\" 2>nul"
        )
        os.system(ps_cmd)
    except Exception:
        pass  # Non critico


# ──────────────────────────────────────────────
#  Regole di monitoraggio
# ──────────────────────────────────────────────

class MonitorEngine:
    """Motore di monitoraggio che valuta regole ad ogni ciclo."""

    def __init__(self, config: dict, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.log = MonitorLog(config.get("log_file", "mt5_monitor_log.json"))
        self.running = True
        self.cycle_count = 0
        self.alerts_fired: set[str] = set()  # Evita alert ripetuti

    def run(self):
        """Loop principale di monitoraggio."""
        interval = self.config.get("interval_seconds", 30)
        max_cycles = self.config.get("max_cycles", 0)  # 0 = infinito

        self.log.log("INFO", f"Monitor avviato (intervallo: {interval}s, dry_run: {self.dry_run})")

        # Registra signal handler per uscita pulita
        signal.signal(signal.SIGINT, self._handle_stop)
        signal.signal(signal.SIGTERM, self._handle_stop)

        while self.running:
            self.cycle_count += 1
            print(f"\n{'='*50}")
            print(f"  Ciclo #{self.cycle_count} — {datetime.now().strftime('%H:%M:%S')}")
            print(f"{'='*50}")

            try:
                self._run_cycle()
            except Exception as e:
                self.log.log("ERROR", f"Errore nel ciclo: {e}")

            if max_cycles > 0 and self.cycle_count >= max_cycles:
                self.log.log("INFO", f"Raggiunto max_cycles ({max_cycles}). Stop.")
                break

            if self.running:
                time.sleep(interval)

        self.log.log("INFO", "Monitor terminato.")

    def _handle_stop(self, signum, frame):
        self.log.log("INFO", "Segnale di stop ricevuto. Uscita...")
        self.running = False

    def _run_cycle(self):
        """Esegue un singolo ciclo di monitoraggio."""
        positions = mt5t.get_positions()
        self.log.log("INFO", f"Posizioni aperte: {len(positions)}")

        rules = self.config.get("rules", [])

        for rule in rules:
            if not rule.get("enabled", True):
                continue
            try:
                self._evaluate_rule(rule, positions)
            except Exception as e:
                self.log.log("ERROR", f"Errore nella regola '{rule.get('name', '?')}': {e}")

    def _evaluate_rule(self, rule: dict, positions: list[dict]):
        """Valuta una singola regola."""
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
        else:
            self.log.log("WARN", f"Tipo regola sconosciuto: {rule_type}")

    # — Trailing Stop automatico —
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
                continue  # Solo posizioni in profitto

            self.log.log("ACTION", f"Trailing stop su #{pos['ticket']} ({pos['symbol']}): {trail_points} punti")
            if not self.dry_run:
                result = mt5t.apply_trailing_stop(pos["ticket"], trail_points)
                self.log.log("INFO", f"  → {result.get('status', 'unknown')}", result)

    # — Break-even automatico —
    def _rule_breakeven(self, rule: dict, positions: list[dict]):
        min_profit_points = rule.get("min_profit_points", 100)
        offset = rule.get("offset_points", 5)
        symbol_filter = rule.get("symbol")

        for pos in positions:
            if symbol_filter and pos["symbol"] != symbol_filter:
                continue
            # Verifica che il profitto in punti sia sufficiente
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
                    f"Break-even su #{pos['ticket']} ({pos['symbol']}): profit {profit_points:.0f} pt > {min_profit_points} pt")
                if not self.dry_run:
                    result = mt5t.move_to_breakeven(pos["ticket"], offset_points=offset)
                    self.log.log("INFO", f"  → {result.get('status', 'unknown')}", result)

    # — Alert su prezzo —
    def _rule_price_alert(self, rule: dict):
        symbol = rule["symbol"]
        alert_id = f"price_{symbol}_{rule.get('level', '')}_{rule.get('direction', '')}"
        if alert_id in self.alerts_fired:
            return  # Già notificato

        tick = mt5t.get_tick(symbol)
        price = tick["bid"]
        level = rule["level"]
        direction = rule.get("direction", "above")  # "above" o "below"

        triggered = (direction == "above" and price >= level) or \
                    (direction == "below" and price <= level)

        if triggered:
            msg = f"ALERT: {symbol} ha {'superato' if direction == 'above' else 'rotto'} {level} (attuale: {price})"
            self.log.log("ALERT", msg)
            self.alerts_fired.add(alert_id)
            if rule.get("notify_desktop", False):
                _notify_desktop("MT5 Price Alert", msg)

            # Azione opzionale
            if "action" in rule:
                self.log.log("ACTION", f"Eseguo azione su alert: {rule['action']}")
                if not self.dry_run:
                    from mt5_strategy_executor import execute_action
                    result = execute_action(rule["action"])
                    self.log.log("INFO", f"  → Risultato azione", result)

    # — Chiudi su profitto —
    def _rule_close_on_profit(self, rule: dict, positions: list[dict]):
        target_profit = rule["target_profit"]  # In valuta account
        symbol_filter = rule.get("symbol")
        magic_filter = rule.get("magic")

        for pos in positions:
            if symbol_filter and pos["symbol"] != symbol_filter:
                continue
            if magic_filter is not None and pos["magic"] != magic_filter:
                continue

            if pos["profit"] >= target_profit:
                self.log.log("ACTION",
                    f"Chiusura per profitto #{pos['ticket']}: {pos['profit']:.2f} >= {target_profit}")
                if not self.dry_run:
                    result = mt5t.close_position(pos["ticket"])
                    self.log.log("INFO", f"  → {result.get('status', 'unknown')}", result)

    # — Chiudi su perdita —
    def _rule_close_on_loss(self, rule: dict, positions: list[dict]):
        max_loss = rule["max_loss"]  # In valuta account (positivo)
        symbol_filter = rule.get("symbol")

        for pos in positions:
            if symbol_filter and pos["symbol"] != symbol_filter:
                continue

            if pos["profit"] <= -abs(max_loss):
                self.log.log("ACTION",
                    f"Chiusura per perdita #{pos['ticket']}: {pos['profit']:.2f} <= -{max_loss}")
                if not self.dry_run:
                    result = mt5t.close_position(pos["ticket"])
                    self.log.log("INFO", f"  → {result.get('status', 'unknown')}", result)

    # — Chiudi a orario —
    def _rule_close_on_time(self, rule: dict, positions: list[dict]):
        close_time = rule["close_after"]  # Formato "HH:MM"
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
                    f"Chiusura per orario #{pos['ticket']} ({pos['symbol']}): dopo {close_time}")
                if not self.dry_run:
                    result = mt5t.close_position(pos["ticket"])
                    self.log.log("INFO", f"  → {result.get('status', 'unknown')}", result)

    # — Alert su indicatori —
    def _rule_indicator_alert(self, rule: dict):
        if not HAS_INDICATORS:
            self.log.log("WARN", "mt5_indicators non disponibile per indicator_alert")
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
                msg = f"RSI overbought su {symbol}: {rsi_val:.1f} > {threshold}"

        elif indicator == "rsi_oversold":
            rsi_val = analysis["indicators"]["rsi_14"]
            threshold = rule.get("threshold", 30)
            if rsi_val and rsi_val < threshold:
                triggered = True
                msg = f"RSI oversold su {symbol}: {rsi_val:.1f} < {threshold}"

        elif indicator == "macd_bullish_cross":
            hist = analysis["indicators"]["macd_histogram"]
            if hist and hist > 0:
                triggered = True
                msg = f"MACD bullish cross su {symbol}: histogram = {hist:.6f}"

        elif indicator == "macd_bearish_cross":
            hist = analysis["indicators"]["macd_histogram"]
            if hist and hist < 0:
                triggered = True
                msg = f"MACD bearish cross su {symbol}: histogram = {hist:.6f}"

        elif indicator == "bb_upper_breakout":
            price = analysis["current_price"]
            bb_upper = analysis["indicators"]["bb_upper"]
            if bb_upper and price > bb_upper:
                triggered = True
                msg = f"Bollinger upper breakout su {symbol}: {price} > {bb_upper}"

        elif indicator == "bb_lower_breakout":
            price = analysis["current_price"]
            bb_lower = analysis["indicators"]["bb_lower"]
            if bb_lower and price < bb_lower:
                triggered = True
                msg = f"Bollinger lower breakout su {symbol}: {price} < {bb_lower}"

        if triggered:
            self.log.log("ALERT", msg)
            self.alerts_fired.add(alert_id)
            if rule.get("notify_desktop", False):
                _notify_desktop("MT5 Indicator Alert", msg)
            if "action" in rule:
                self.log.log("ACTION", f"Eseguo azione: {rule['action']}")
                if not self.dry_run:
                    from mt5_strategy_executor import execute_action
                    result = execute_action(rule["action"])
                    self.log.log("INFO", f"  → Risultato", result)

    # — Max Drawdown —
    def _rule_max_drawdown(self, rule: dict, positions: list[dict]):
        max_dd_percent = rule["max_drawdown_percent"]
        acc = mt5.account_info()
        if not acc:
            return

        dd = ((acc.balance - acc.equity) / acc.balance) * 100 if acc.balance > 0 else 0

        if dd >= max_dd_percent:
            msg = f"DRAWDOWN CRITICO: {dd:.2f}% >= {max_dd_percent}%"
            self.log.log("ALERT", msg)
            if rule.get("close_all", False):
                self.log.log("ACTION", "Chiusura di TUTTE le posizioni per max drawdown!")
                if not self.dry_run:
                    result = mt5t.close_all_positions()
                    self.log.log("INFO", "Risultato chiusura totale", result)


# ──────────────────────────────────────────────
#  Config di esempio
# ──────────────────────────────────────────────

EXAMPLE_CONFIG = {
    "description": "Configurazione di esempio per MT5 Monitor",
    "interval_seconds": 30,
    "max_cycles": 0,
    "log_file": "mt5_monitor_log.json",
    "rules": [
        {
            "name": "Trailing stop globale",
            "type": "trailing_stop",
            "enabled": True,
            "trail_points": 200,
            "comment": "Applica trailing stop di 200 punti a tutte le posizioni in profitto"
        },
        {
            "name": "Break-even EURUSD",
            "type": "breakeven",
            "enabled": True,
            "symbol": "EURUSD",
            "min_profit_points": 150,
            "offset_points": 5,
            "comment": "Sposta a BE quando il profitto supera 15 pips"
        },
        {
            "name": "Alert breakout EURUSD",
            "type": "price_alert",
            "enabled": False,
            "symbol": "EURUSD",
            "level": 1.1000,
            "direction": "above",
            "notify_desktop": True,
            "comment": "Avvisa se EURUSD rompe 1.1000"
        },
        {
            "name": "Take profit a 50€",
            "type": "close_on_profit",
            "enabled": False,
            "target_profit": 50.0,
            "comment": "Chiudi posizioni con profitto >= 50€"
        },
        {
            "name": "Stop loss a 30€",
            "type": "close_on_loss",
            "enabled": False,
            "max_loss": 30.0,
            "comment": "Chiudi posizioni con perdita >= 30€"
        },
        {
            "name": "Chiusura fine giornata",
            "type": "close_on_time",
            "enabled": False,
            "close_after": "21:30",
            "comment": "Chiudi tutto dopo le 21:30"
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
            "comment": "Alert quando RSI > 75"
        },
        {
            "name": "Max drawdown 5%",
            "type": "max_drawdown",
            "enabled": True,
            "max_drawdown_percent": 5.0,
            "close_all": True,
            "comment": "Chiudi TUTTO se il drawdown supera il 5%"
        }
    ]
}


# ──────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MT5 Monitor — Monitoraggio continuo")
    parser.add_argument("config", nargs="?", help="File di configurazione JSON")
    parser.add_argument("--generate-config", action="store_true", help="Genera config di esempio")
    parser.add_argument("--dry-run", action="store_true", help="Simula senza eseguire azioni")
    parser.add_argument("--interval", type=int, help="Override intervallo in secondi")
    args = parser.parse_args()

    if args.generate_config:
        out_path = "mt5_monitor_config.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(EXAMPLE_CONFIG, f, indent=2, ensure_ascii=False)
        print(f"Config di esempio salvata in: {out_path}")
        sys.exit(0)

    if not args.config:
        parser.print_help()
        sys.exit(1)

    with open(args.config, encoding="utf-8") as f:
        config = json.load(f)

    if args.interval:
        config["interval_seconds"] = args.interval

    # Connetti a MT5
    print("Connessione a MT5...")
    try:
        info = mt5t.connect()
        print(f"Connesso: {info['name']} | Saldo: {info['balance']} {info['currency']}\n")
    except Exception as e:
        print(f"Errore connessione: {e}", file=sys.stderr)
        sys.exit(1)

    # Avvia monitor
    engine = MonitorEngine(config, dry_run=args.dry_run)
    try:
        engine.run()
    finally:
        mt5t.disconnect()
        print("\nDisconnesso da MT5.")


if __name__ == "__main__":
    main()
