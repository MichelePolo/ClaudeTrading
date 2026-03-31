#!/usr/bin/env python3
"""
MT5 Trading Library — Utility completa per MetaTrader 5.

Operazioni supportate:
  - Connessione / disconnessione a MT5
  - Info account e simboli
  - Apertura ordini (market & pending)
  - Chiusura totale o parziale
  - Modifica SL / TP
  - Trailing stop
  - Query posizioni e ordini pendenti
  - Calcolo lotto da rischio percentuale
  - Chiusura multipla (per simbolo, per magic, tutte)

Requisiti:
  pip install MetaTrader5

Uso da CLI:
  python mt5_trading.py --help
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from typing import Optional

try:
    import MetaTrader5 as mt5
except ImportError:
    print(
        "ERROR: MetaTrader5 package not installed.\n"
        "Install with:  pip install MetaTrader5\n"
        "Requires Windows with MetaTrader 5 terminal installed.",
        file=sys.stderr,
    )
    sys.exit(1)


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _json_out(data: dict | list, pretty: bool = True) -> str:
    """Serializza in JSON human-readable."""
    return json.dumps(data, indent=2 if pretty else None, default=str, ensure_ascii=False)


def _check_initialized():
    """Verifica che MT5 sia inizializzato."""
    if not mt5.terminal_info():
        raise RuntimeError(
            "MT5 non inizializzato. Chiama prima 'connect' o esegui: "
            "python mt5_trading.py connect"
        )


def _last_error() -> str:
    err = mt5.last_error()
    return f"[{err[0]}] {err[1]}" if err else "Errore sconosciuto"


def _position_to_dict(pos) -> dict:
    return {
        "ticket": pos.ticket,
        "symbol": pos.symbol,
        "type": "BUY" if pos.type == mt5.ORDER_TYPE_BUY else "SELL",
        "volume": pos.volume,
        "price_open": pos.price_open,
        "price_current": pos.price_current,
        "sl": pos.sl,
        "tp": pos.tp,
        "profit": pos.profit,
        "swap": pos.swap,
        "magic": pos.magic,
        "comment": pos.comment,
        "time": str(datetime.fromtimestamp(pos.time, tz=timezone.utc)),
    }


def _order_to_dict(order) -> dict:
    type_map = {
        mt5.ORDER_TYPE_BUY_LIMIT: "BUY_LIMIT",
        mt5.ORDER_TYPE_SELL_LIMIT: "SELL_LIMIT",
        mt5.ORDER_TYPE_BUY_STOP: "BUY_STOP",
        mt5.ORDER_TYPE_SELL_STOP: "SELL_STOP",
        mt5.ORDER_TYPE_BUY_STOP_LIMIT: "BUY_STOP_LIMIT",
        mt5.ORDER_TYPE_SELL_STOP_LIMIT: "SELL_STOP_LIMIT",
    }
    return {
        "ticket": order.ticket,
        "symbol": order.symbol,
        "type": type_map.get(order.type, str(order.type)),
        "volume": order.volume_current,
        "price": order.price_open,
        "sl": order.sl,
        "tp": order.tp,
        "magic": order.magic,
        "comment": order.comment,
        "time": str(datetime.fromtimestamp(order.time_setup, tz=timezone.utc)),
    }


# ──────────────────────────────────────────────
#  Connessione
# ──────────────────────────────────────────────

def connect(
    path: Optional[str] = None,
    login: Optional[int] = None,
    password: Optional[str] = None,
    server: Optional[str] = None,
    timeout: int = 10_000,
) -> dict:
    """Inizializza la connessione a MetaTrader 5.

    Args:
        path: Percorso dell'eseguibile terminal64.exe (opzionale).
        login: Numero account (opzionale se già loggato).
        password: Password account.
        server: Nome server broker.
        timeout: Timeout connessione in ms.

    Returns:
        dict con info account.
    """
    kwargs = {"timeout": timeout}
    if path:
        kwargs["path"] = path
    if login:
        kwargs["login"] = login
    if password:
        kwargs["password"] = password
    if server:
        kwargs["server"] = server

    if not mt5.initialize(**kwargs):
        raise RuntimeError(f"Impossibile inizializzare MT5: {_last_error()}")

    info = mt5.account_info()
    if info is None:
        raise RuntimeError(f"Impossibile ottenere info account: {_last_error()}")

    return {
        "status": "connected",
        "login": info.login,
        "server": info.server,
        "name": info.name,
        "balance": info.balance,
        "equity": info.equity,
        "margin_free": info.margin_free,
        "currency": info.currency,
        "leverage": info.leverage,
    }


def disconnect() -> dict:
    """Chiude la connessione a MT5."""
    mt5.shutdown()
    return {"status": "disconnected"}


# ──────────────────────────────────────────────
#  Info
# ──────────────────────────────────────────────

def account_info() -> dict:
    """Restituisce informazioni sull'account corrente."""
    _check_initialized()
    info = mt5.account_info()
    if info is None:
        raise RuntimeError(f"Errore account_info: {_last_error()}")
    return {
        "login": info.login,
        "server": info.server,
        "name": info.name,
        "balance": info.balance,
        "equity": info.equity,
        "profit": info.profit,
        "margin": info.margin,
        "margin_free": info.margin_free,
        "margin_level": info.margin_level,
        "currency": info.currency,
        "leverage": info.leverage,
    }


def symbol_info(symbol: str) -> dict:
    """Restituisce informazioni su un simbolo."""
    _check_initialized()
    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"Simbolo '{symbol}' non trovato: {_last_error()}")
    # Abilita il simbolo nel Market Watch se necessario
    if not info.visible:
        mt5.symbol_select(symbol, True)
    tick = mt5.symbol_info_tick(symbol)
    return {
        "symbol": symbol,
        "bid": tick.bid if tick else None,
        "ask": tick.ask if tick else None,
        "spread": info.spread,
        "digits": info.digits,
        "point": info.point,
        "volume_min": info.volume_min,
        "volume_max": info.volume_max,
        "volume_step": info.volume_step,
        "trade_contract_size": info.trade_contract_size,
        "currency_profit": info.currency_profit,
    }


# ──────────────────────────────────────────────
#  Posizioni e ordini
# ──────────────────────────────────────────────

def get_positions(symbol: Optional[str] = None, magic: Optional[int] = None) -> list[dict]:
    """Elenca posizioni aperte, con filtro opzionale per simbolo/magic."""
    _check_initialized()
    if symbol:
        positions = mt5.positions_get(symbol=symbol)
    else:
        positions = mt5.positions_get()

    if positions is None:
        return []

    result = [_position_to_dict(p) for p in positions]
    if magic is not None:
        result = [p for p in result if p["magic"] == magic]
    return result


def get_pending_orders(symbol: Optional[str] = None) -> list[dict]:
    """Elenca ordini pendenti."""
    _check_initialized()
    if symbol:
        orders = mt5.orders_get(symbol=symbol)
    else:
        orders = mt5.orders_get()

    if orders is None:
        return []
    return [_order_to_dict(o) for o in orders]


# ──────────────────────────────────────────────
#  Calcolo lotto
# ──────────────────────────────────────────────

def calculate_lot_size(
    symbol: str,
    risk_percent: float,
    sl_points: float,
    account_balance: Optional[float] = None,
) -> dict:
    """Calcola il volume (lotti) in base al rischio percentuale.

    Args:
        symbol: Simbolo di trading.
        risk_percent: Percentuale del saldo da rischiare (es. 1.0 = 1%).
        sl_points: Distanza dello stop loss in punti.
        account_balance: Saldo da usare (se None, usa il saldo corrente).

    Returns:
        dict con volume calcolato e dettagli.
    """
    _check_initialized()
    if account_balance is None:
        acc = mt5.account_info()
        account_balance = acc.balance

    info = mt5.symbol_info(symbol)
    if info is None:
        raise RuntimeError(f"Simbolo '{symbol}' non trovato")

    risk_amount = account_balance * (risk_percent / 100.0)
    # Valore di un punto per 1 lotto
    tick_value = info.trade_tick_value
    tick_size = info.trade_tick_size
    point = info.point

    if tick_value <= 0 or tick_size <= 0:
        raise RuntimeError(f"Impossibile calcolare tick_value per {symbol}")

    # Valore monetario per punto per lotto
    value_per_point = tick_value * (point / tick_size)
    raw_lot = risk_amount / (sl_points * value_per_point)

    # Arrotonda al volume_step
    step = info.volume_step
    lot = max(info.volume_min, min(info.volume_max, round(raw_lot / step) * step))
    lot = round(lot, 2)

    return {
        "symbol": symbol,
        "risk_percent": risk_percent,
        "risk_amount": round(risk_amount, 2),
        "sl_points": sl_points,
        "calculated_lot": lot,
        "volume_min": info.volume_min,
        "volume_max": info.volume_max,
        "volume_step": info.volume_step,
    }


# ──────────────────────────────────────────────
#  Apertura ordini
# ──────────────────────────────────────────────

def open_market_order(
    symbol: str,
    direction: str,
    volume: float,
    sl: float = 0.0,
    tp: float = 0.0,
    magic: int = 0,
    comment: str = "",
    deviation: int = 20,
) -> dict:
    """Apre un ordine a mercato (BUY o SELL).

    Args:
        symbol: Simbolo di trading.
        direction: "BUY" o "SELL".
        volume: Volume in lotti.
        sl: Prezzo stop loss (0 = nessuno).
        tp: Prezzo take profit (0 = nessuno).
        magic: Magic number per identificare la strategia.
        comment: Commento ordine.
        deviation: Deviazione massima dal prezzo in punti.

    Returns:
        dict con dettagli dell'ordine eseguito.
    """
    _check_initialized()
    direction = direction.upper()
    if direction not in ("BUY", "SELL"):
        raise ValueError("direction deve essere 'BUY' o 'SELL'")

    # Assicura che il simbolo sia visibile
    mt5.symbol_select(symbol, True)
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"Impossibile ottenere prezzo per {symbol}: {_last_error()}")

    order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
    price = tick.ask if direction == "BUY" else tick.bid

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(volume),
        "type": order_type,
        "price": price,
        "sl": float(sl),
        "tp": float(tp),
        "deviation": deviation,
        "magic": magic,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"order_send ha restituito None: {_last_error()}")
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise RuntimeError(
            f"Ordine rifiutato: [{result.retcode}] {result.comment}"
        )

    return {
        "status": "filled",
        "ticket": result.order,
        "deal": result.deal,
        "symbol": symbol,
        "direction": direction,
        "volume": volume,
        "price": result.price,
        "sl": sl,
        "tp": tp,
        "magic": magic,
        "comment": comment,
    }


def open_pending_order(
    symbol: str,
    order_type: str,
    volume: float,
    price: float,
    sl: float = 0.0,
    tp: float = 0.0,
    magic: int = 0,
    comment: str = "",
    expiration: Optional[str] = None,
) -> dict:
    """Piazza un ordine pendente.

    Args:
        symbol: Simbolo.
        order_type: Uno tra BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP.
        volume: Lotti.
        price: Prezzo dell'ordine.
        sl: Stop loss.
        tp: Take profit.
        magic: Magic number.
        comment: Commento.
        expiration: Data scadenza ISO (es. "2025-12-31T23:59:00"). None = GTC.

    Returns:
        dict con dettagli ordine pendente.
    """
    _check_initialized()
    type_map = {
        "BUY_LIMIT": mt5.ORDER_TYPE_BUY_LIMIT,
        "SELL_LIMIT": mt5.ORDER_TYPE_SELL_LIMIT,
        "BUY_STOP": mt5.ORDER_TYPE_BUY_STOP,
        "SELL_STOP": mt5.ORDER_TYPE_SELL_STOP,
    }
    order_type = order_type.upper()
    if order_type not in type_map:
        raise ValueError(f"order_type deve essere uno di: {list(type_map.keys())}")

    mt5.symbol_select(symbol, True)

    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": float(volume),
        "type": type_map[order_type],
        "price": float(price),
        "sl": float(sl),
        "tp": float(tp),
        "magic": magic,
        "comment": comment,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    if expiration:
        exp_dt = datetime.fromisoformat(expiration)
        request["type_time"] = mt5.ORDER_TIME_SPECIFIED
        request["expiration"] = int(exp_dt.timestamp())
    else:
        request["type_time"] = mt5.ORDER_TIME_GTC

    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"order_send ha restituito None: {_last_error()}")
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise RuntimeError(f"Ordine rifiutato: [{result.retcode}] {result.comment}")

    return {
        "status": "placed",
        "ticket": result.order,
        "symbol": symbol,
        "order_type": order_type,
        "volume": volume,
        "price": price,
        "sl": sl,
        "tp": tp,
        "magic": magic,
    }


# ──────────────────────────────────────────────
#  Chiusura
# ──────────────────────────────────────────────

def close_position(ticket: int, volume: Optional[float] = None, deviation: int = 20) -> dict:
    """Chiude una posizione per ticket (totale o parziale).

    Args:
        ticket: Ticket della posizione.
        volume: Volume da chiudere. None = chiudi tutto.
        deviation: Deviazione max in punti.

    Returns:
        dict con risultato chiusura.
    """
    _check_initialized()
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        raise RuntimeError(f"Posizione con ticket {ticket} non trovata")

    pos = positions[0]
    close_vol = volume if volume else pos.volume

    # Ordine opposto
    close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY
    tick = mt5.symbol_info_tick(pos.symbol)
    price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": pos.symbol,
        "volume": float(close_vol),
        "type": close_type,
        "position": ticket,
        "price": price,
        "deviation": deviation,
        "magic": pos.magic,
        "comment": f"close #{ticket}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"Chiusura fallita: {_last_error()}")
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise RuntimeError(f"Chiusura rifiutata: [{result.retcode}] {result.comment}")

    return {
        "status": "closed",
        "ticket": ticket,
        "volume_closed": close_vol,
        "price": result.price,
        "remaining": round(pos.volume - close_vol, 2) if volume else 0,
    }


def close_all_positions(symbol: Optional[str] = None, magic: Optional[int] = None) -> dict:
    """Chiude tutte le posizioni aperte (con filtro opzionale).

    Args:
        symbol: Solo posizioni su questo simbolo.
        magic: Solo posizioni con questo magic number.

    Returns:
        dict con riepilogo chiusure.
    """
    positions = get_positions(symbol=symbol, magic=magic)
    results = {"closed": [], "errors": []}

    for pos in positions:
        try:
            res = close_position(pos["ticket"])
            results["closed"].append(res)
        except RuntimeError as e:
            results["errors"].append({"ticket": pos["ticket"], "error": str(e)})

    results["total_closed"] = len(results["closed"])
    results["total_errors"] = len(results["errors"])
    return results


def cancel_pending_order(ticket: int) -> dict:
    """Cancella un ordine pendente.

    Args:
        ticket: Ticket dell'ordine pendente.

    Returns:
        dict con risultato.
    """
    _check_initialized()
    request = {
        "action": mt5.TRADE_ACTION_REMOVE,
        "order": ticket,
    }
    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"Cancellazione fallita: {_last_error()}")
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise RuntimeError(f"Cancellazione rifiutata: [{result.retcode}] {result.comment}")

    return {"status": "cancelled", "ticket": ticket}


def cancel_all_pending_orders(symbol: Optional[str] = None) -> dict:
    """Cancella tutti gli ordini pendenti."""
    orders = get_pending_orders(symbol=symbol)
    results = {"cancelled": [], "errors": []}

    for o in orders:
        try:
            res = cancel_pending_order(o["ticket"])
            results["cancelled"].append(res)
        except RuntimeError as e:
            results["errors"].append({"ticket": o["ticket"], "error": str(e)})

    results["total_cancelled"] = len(results["cancelled"])
    return results


# ──────────────────────────────────────────────
#  Modifica posizioni
# ──────────────────────────────────────────────

def modify_position(ticket: int, sl: Optional[float] = None, tp: Optional[float] = None) -> dict:
    """Modifica SL e/o TP di una posizione aperta.

    Args:
        ticket: Ticket della posizione.
        sl: Nuovo stop loss (None = invariato).
        tp: Nuovo take profit (None = invariato).

    Returns:
        dict con risultato modifica.
    """
    _check_initialized()
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        raise RuntimeError(f"Posizione {ticket} non trovata")

    pos = positions[0]
    new_sl = sl if sl is not None else pos.sl
    new_tp = tp if tp is not None else pos.tp

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": pos.symbol,
        "position": ticket,
        "sl": float(new_sl),
        "tp": float(new_tp),
    }

    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"Modifica fallita: {_last_error()}")
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise RuntimeError(f"Modifica rifiutata: [{result.retcode}] {result.comment}")

    return {
        "status": "modified",
        "ticket": ticket,
        "sl": new_sl,
        "tp": new_tp,
        "sl_previous": pos.sl,
        "tp_previous": pos.tp,
    }


def modify_pending_order(
    ticket: int,
    price: Optional[float] = None,
    sl: Optional[float] = None,
    tp: Optional[float] = None,
) -> dict:
    """Modifica un ordine pendente.

    Args:
        ticket: Ticket dell'ordine.
        price: Nuovo prezzo (None = invariato).
        sl: Nuovo SL (None = invariato).
        tp: Nuovo TP (None = invariato).

    Returns:
        dict con risultato modifica.
    """
    _check_initialized()
    orders = mt5.orders_get(ticket=ticket)
    if not orders:
        raise RuntimeError(f"Ordine pendente {ticket} non trovato")

    order = orders[0]
    new_price = price if price is not None else order.price_open
    new_sl = sl if sl is not None else order.sl
    new_tp = tp if tp is not None else order.tp

    request = {
        "action": mt5.TRADE_ACTION_MODIFY,
        "order": ticket,
        "price": float(new_price),
        "sl": float(new_sl),
        "tp": float(new_tp),
        "type_time": mt5.ORDER_TIME_GTC,
    }

    result = mt5.order_send(request)
    if result is None:
        raise RuntimeError(f"Modifica fallita: {_last_error()}")
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        raise RuntimeError(f"Modifica rifiutata: [{result.retcode}] {result.comment}")

    return {
        "status": "modified",
        "ticket": ticket,
        "price": new_price,
        "sl": new_sl,
        "tp": new_tp,
    }


# ──────────────────────────────────────────────
#  Trailing Stop
# ──────────────────────────────────────────────

def apply_trailing_stop(ticket: int, trail_points: float) -> dict:
    """Applica un trailing stop a una posizione.

    Sposta lo SL solo se il prezzo si è mosso a favore oltre trail_points.

    Args:
        ticket: Ticket della posizione.
        trail_points: Distanza trailing in punti dal prezzo corrente.

    Returns:
        dict con risultato (modified o unchanged).
    """
    _check_initialized()
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        raise RuntimeError(f"Posizione {ticket} non trovata")

    pos = positions[0]
    info = mt5.symbol_info(pos.symbol)
    point = info.point
    trail_distance = trail_points * point

    if pos.type == mt5.ORDER_TYPE_BUY:
        new_sl = pos.price_current - trail_distance
        # Sposta solo se il nuovo SL è meglio del precedente
        if new_sl > pos.sl:
            return modify_position(ticket, sl=round(new_sl, info.digits))
    else:  # SELL
        new_sl = pos.price_current + trail_distance
        if pos.sl == 0 or new_sl < pos.sl:
            return modify_position(ticket, sl=round(new_sl, info.digits))

    return {
        "status": "unchanged",
        "ticket": ticket,
        "reason": "Il trailing stop non ha migliorato lo SL corrente",
        "current_sl": pos.sl,
        "calculated_sl": round(new_sl, info.digits),
    }


# ──────────────────────────────────────────────
#  Break Even
# ──────────────────────────────────────────────

def move_to_breakeven(ticket: int, offset_points: float = 0) -> dict:
    """Sposta lo SL al prezzo di apertura (break even) + offset opzionale.

    Args:
        ticket: Ticket della posizione.
        offset_points: Punti extra oltre il break-even (per coprire commissioni).

    Returns:
        dict con risultato.
    """
    _check_initialized()
    positions = mt5.positions_get(ticket=ticket)
    if not positions:
        raise RuntimeError(f"Posizione {ticket} non trovata")

    pos = positions[0]
    info = mt5.symbol_info(pos.symbol)
    point = info.point

    if pos.type == mt5.ORDER_TYPE_BUY:
        be_price = pos.price_open + (offset_points * point)
        if pos.price_current < be_price:
            return {"status": "skipped", "reason": "Prezzo ancora sotto break-even"}
    else:
        be_price = pos.price_open - (offset_points * point)
        if pos.price_current > be_price:
            return {"status": "skipped", "reason": "Prezzo ancora sopra break-even"}

    return modify_position(ticket, sl=round(be_price, info.digits))


# ──────────────────────────────────────────────
#  Market Data
# ──────────────────────────────────────────────

def get_tick(symbol: str) -> dict:
    """Ottieni l'ultimo tick (bid/ask) per un simbolo."""
    _check_initialized()
    mt5.symbol_select(symbol, True)
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        raise RuntimeError(f"Impossibile ottenere tick per {symbol}: {_last_error()}")
    return {
        "symbol": symbol,
        "bid": tick.bid,
        "ask": tick.ask,
        "last": tick.last,
        "volume": tick.volume,
        "time": str(datetime.fromtimestamp(tick.time, tz=timezone.utc)),
    }


def get_ohlc(symbol: str, timeframe: str = "H1", count: int = 100) -> list[dict]:
    """Scarica barre OHLC.

    Args:
        symbol: Simbolo.
        timeframe: Timeframe stringa (M1, M5, M15, M30, H1, H4, D1, W1, MN1).
        count: Numero di barre.

    Returns:
        Lista di dict con open, high, low, close, volume, time.
    """
    _check_initialized()
    tf_map = {
        "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5,
        "M15": mt5.TIMEFRAME_M15, "M30": mt5.TIMEFRAME_M30,
        "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
        "D1": mt5.TIMEFRAME_D1, "W1": mt5.TIMEFRAME_W1,
        "MN1": mt5.TIMEFRAME_MN1,
    }
    tf = tf_map.get(timeframe.upper())
    if tf is None:
        raise ValueError(f"Timeframe '{timeframe}' non valido. Usa: {list(tf_map.keys())}")

    mt5.symbol_select(symbol, True)
    rates = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rates is None or len(rates) == 0:
        raise RuntimeError(f"Nessun dato per {symbol} {timeframe}: {_last_error()}")

    return [
        {
            "time": str(datetime.fromtimestamp(r[0], tz=timezone.utc)),
            "open": r[1],
            "high": r[2],
            "low": r[3],
            "close": r[4],
            "tick_volume": int(r[5]),
            "spread": int(r[6]),
            "real_volume": int(r[7]),
        }
        for r in rates
    ]


# ──────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="MT5 Trading CLI — Gestisci trade da riga di comando",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="Comando da eseguire")

    # connect
    p = sub.add_parser("connect", help="Connetti a MT5")
    p.add_argument("--path", help="Percorso terminal64.exe")
    p.add_argument("--login", type=int, help="Numero account")
    p.add_argument("--password", help="Password account")
    p.add_argument("--server", help="Nome server broker")

    # disconnect
    sub.add_parser("disconnect", help="Disconnetti da MT5")

    # account
    sub.add_parser("account", help="Info account")

    # symbol
    p = sub.add_parser("symbol", help="Info simbolo")
    p.add_argument("symbol", help="Nome simbolo (es. EURUSD)")

    # tick
    p = sub.add_parser("tick", help="Ultimo tick")
    p.add_argument("symbol", help="Nome simbolo")

    # ohlc
    p = sub.add_parser("ohlc", help="Dati OHLC")
    p.add_argument("symbol", help="Nome simbolo")
    p.add_argument("--timeframe", default="H1", help="Timeframe (M1,M5,M15,M30,H1,H4,D1,W1,MN1)")
    p.add_argument("--count", type=int, default=20, help="Numero barre")

    # positions
    p = sub.add_parser("positions", help="Posizioni aperte")
    p.add_argument("--symbol", help="Filtra per simbolo")
    p.add_argument("--magic", type=int, help="Filtra per magic number")

    # pending
    p = sub.add_parser("pending", help="Ordini pendenti")
    p.add_argument("--symbol", help="Filtra per simbolo")

    # buy / sell
    for cmd in ("buy", "sell"):
        p = sub.add_parser(cmd, help=f"Ordine {cmd.upper()} a mercato")
        p.add_argument("symbol", help="Simbolo")
        p.add_argument("volume", type=float, help="Volume in lotti")
        p.add_argument("--sl", type=float, default=0, help="Stop loss")
        p.add_argument("--tp", type=float, default=0, help="Take profit")
        p.add_argument("--magic", type=int, default=0, help="Magic number")
        p.add_argument("--comment", default="", help="Commento")

    # pending order
    p = sub.add_parser("pending_order", help="Ordine pendente")
    p.add_argument("symbol", help="Simbolo")
    p.add_argument("type", help="BUY_LIMIT, SELL_LIMIT, BUY_STOP, SELL_STOP")
    p.add_argument("volume", type=float, help="Volume")
    p.add_argument("price", type=float, help="Prezzo ordine")
    p.add_argument("--sl", type=float, default=0, help="Stop loss")
    p.add_argument("--tp", type=float, default=0, help="Take profit")
    p.add_argument("--magic", type=int, default=0, help="Magic number")
    p.add_argument("--comment", default="", help="Commento")

    # close
    p = sub.add_parser("close", help="Chiudi posizione")
    p.add_argument("ticket", type=int, help="Ticket posizione")
    p.add_argument("--volume", type=float, help="Volume parziale (ometti per chiusura totale)")

    # close_all
    p = sub.add_parser("close_all", help="Chiudi tutte le posizioni")
    p.add_argument("--symbol", help="Solo questo simbolo")
    p.add_argument("--magic", type=int, help="Solo questo magic number")

    # cancel
    p = sub.add_parser("cancel", help="Cancella ordine pendente")
    p.add_argument("ticket", type=int, help="Ticket ordine")

    # cancel_all
    p = sub.add_parser("cancel_all", help="Cancella tutti gli ordini pendenti")
    p.add_argument("--symbol", help="Solo questo simbolo")

    # modify
    p = sub.add_parser("modify", help="Modifica SL/TP posizione")
    p.add_argument("ticket", type=int, help="Ticket posizione")
    p.add_argument("--sl", type=float, help="Nuovo stop loss")
    p.add_argument("--tp", type=float, help="Nuovo take profit")

    # modify_pending
    p = sub.add_parser("modify_pending", help="Modifica ordine pendente")
    p.add_argument("ticket", type=int, help="Ticket ordine")
    p.add_argument("--price", type=float, help="Nuovo prezzo")
    p.add_argument("--sl", type=float, help="Nuovo SL")
    p.add_argument("--tp", type=float, help="Nuovo TP")

    # trailing
    p = sub.add_parser("trailing", help="Applica trailing stop")
    p.add_argument("ticket", type=int, help="Ticket posizione")
    p.add_argument("points", type=float, help="Distanza trailing in punti")

    # breakeven
    p = sub.add_parser("breakeven", help="Sposta SL a break-even")
    p.add_argument("ticket", type=int, help="Ticket posizione")
    p.add_argument("--offset", type=float, default=0, help="Punti extra oltre BE")

    # lot_size
    p = sub.add_parser("lot_size", help="Calcola lotto da rischio %")
    p.add_argument("symbol", help="Simbolo")
    p.add_argument("risk", type=float, help="Rischio percentuale (es. 1.0)")
    p.add_argument("sl_points", type=float, help="Distanza SL in punti")

    return parser


def main():
    parser = _build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    try:
        if args.command == "connect":
            result = connect(path=args.path, login=args.login,
                             password=args.password, server=args.server)
        elif args.command == "disconnect":
            result = disconnect()
        elif args.command == "account":
            result = account_info()
        elif args.command == "symbol":
            result = symbol_info(args.symbol)
        elif args.command == "tick":
            result = get_tick(args.symbol)
        elif args.command == "ohlc":
            result = get_ohlc(args.symbol, args.timeframe, args.count)
        elif args.command == "positions":
            result = get_positions(symbol=args.symbol, magic=args.magic)
        elif args.command == "pending":
            result = get_pending_orders(symbol=args.symbol)
        elif args.command in ("buy", "sell"):
            result = open_market_order(
                symbol=args.symbol, direction=args.command.upper(),
                volume=args.volume, sl=args.sl, tp=args.tp,
                magic=args.magic, comment=args.comment,
            )
        elif args.command == "pending_order":
            result = open_pending_order(
                symbol=args.symbol, order_type=args.type,
                volume=args.volume, price=args.price,
                sl=args.sl, tp=args.tp, magic=args.magic,
                comment=args.comment,
            )
        elif args.command == "close":
            result = close_position(args.ticket, volume=args.volume)
        elif args.command == "close_all":
            result = close_all_positions(symbol=args.symbol, magic=args.magic)
        elif args.command == "cancel":
            result = cancel_pending_order(args.ticket)
        elif args.command == "cancel_all":
            result = cancel_all_pending_orders(symbol=args.symbol)
        elif args.command == "modify":
            result = modify_position(args.ticket, sl=args.sl, tp=args.tp)
        elif args.command == "modify_pending":
            result = modify_pending_order(args.ticket, price=args.price,
                                          sl=args.sl, tp=args.tp)
        elif args.command == "trailing":
            result = apply_trailing_stop(args.ticket, args.points)
        elif args.command == "breakeven":
            result = move_to_breakeven(args.ticket, offset_points=args.offset)
        elif args.command == "lot_size":
            result = calculate_lot_size(args.symbol, args.risk, args.sl_points)
        else:
            parser.print_help()
            sys.exit(1)

        print(_json_out(result))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
