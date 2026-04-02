#!/usr/bin/env python3
"""
MT5 Technical Indicators — Technical indicators computed on MT5 OHLC data.

Available indicators:
  - SMA (Simple Moving Average)
  - EMA (Exponential Moving Average)
  - TEMA (Triple Exponential Moving Average — low-lag trend filter)
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - Bollinger Bands
  - ATR (Average True Range)
  - Stochastic Oscillator
  - ADX (Average Directional Index)
  - Pivot Points (classic, Fibonacci, Camarilla)
  - Support and Resistance from swing points

Requirements:
  pip install MetaTrader5

CLI usage:
  python mt5_indicators.py EURUSD --timeframe H1 --indicators rsi macd bbands
  python mt5_indicators.py EURUSD --indicators tema   # TEMA only
  python mt5_indicators.py EURUSD --analysis           # Full analysis (includes TEMA)
  python mt5_indicators.py EURUSD --pivots             # Daily pivot points

Library usage:
  from mt5_indicators import get_analysis
  result = get_analysis("EURUSD", timeframe="H1")
"""

from __future__ import annotations

import argparse
import json
import sys
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


# ──────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────

def _get_closes(symbol: str, timeframe: str = "H1", count: int = 200) -> tuple[list[dict], list[float]]:
    """Download OHLC bars and return (bars, closes)."""
    bars = mt5t.get_ohlc(symbol, timeframe, count)
    closes = [b["close"] for b in bars]
    return bars, closes


def _get_hlc(bars: list[dict]) -> tuple[list[float], list[float], list[float]]:
    highs = [b["high"] for b in bars]
    lows = [b["low"] for b in bars]
    closes = [b["close"] for b in bars]
    return highs, lows, closes


# ──────────────────────────────────────────────
#  SMA / EMA
# ──────────────────────────────────────────────

def sma(values: list[float], period: int) -> list[Optional[float]]:
    """Simple Moving Average."""
    result = [None] * len(values)
    for i in range(period - 1, len(values)):
        result[i] = sum(values[i - period + 1 : i + 1]) / period
    return result


def ema(values: list[float], period: int) -> list[Optional[float]]:
    """Exponential Moving Average."""
    result = [None] * len(values)
    k = 2.0 / (period + 1)
    # First EMA = SMA
    first_sma = sum(values[:period]) / period
    result[period - 1] = first_sma
    for i in range(period, len(values)):
        result[i] = values[i] * k + result[i - 1] * (1 - k)
    return result


def tema(values: list[float], period: int) -> list[Optional[float]]:
    """Triple Exponential Moving Average (TEMA).

    Formula: TEMA = 3*EMA1 - 3*EMA2 + EMA3
    where EMA2 = EMA(EMA1) and EMA3 = EMA(EMA2).

    Reduces lag compared to a standard EMA.
    """
    ema1 = ema(values, period)

    # EMA2 = EMA of EMA1 (only valid values)
    valid1 = [v for v in ema1 if v is not None]
    if len(valid1) < period:
        return [None] * len(values)
    ema2_raw = ema(valid1, period)

    valid2 = [v for v in ema2_raw if v is not None]
    if len(valid2) < period:
        return [None] * len(values)
    ema3_raw = ema(valid2, period)

    # Remap EMA2 and EMA3 back to original length
    offset1 = len(values) - len(valid1)
    ema2 = [None] * len(values)
    for i, v in enumerate(ema2_raw):
        ema2[i + offset1] = v

    offset2 = len(values) - len(valid2)
    ema3 = [None] * len(values)
    for i, v in enumerate(ema3_raw):
        ema3[i + offset2] = v

    result = [None] * len(values)
    for i in range(len(values)):
        if ema1[i] is not None and ema2[i] is not None and ema3[i] is not None:
            result[i] = 3 * ema1[i] - 3 * ema2[i] + ema3[i]
    return result


# ──────────────────────────────────────────────
#  RSI
# ──────────────────────────────────────────────

def rsi(values: list[float], period: int = 14) -> list[Optional[float]]:
    """Relative Strength Index (Wilder/smoothed method)."""
    result = [None] * len(values)
    if len(values) < period + 1:
        return result

    # Compute changes
    deltas = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    # First average
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100 - (100 / (1 + rs))

    # Smoothed
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            result[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100 - (100 / (1 + rs))

    return result


# ──────────────────────────────────────────────
#  MACD
# ──────────────────────────────────────────────

def macd(
    values: list[float],
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> dict:
    """MACD with line, signal, and histogram."""
    ema_fast = ema(values, fast)
    ema_slow = ema(values, slow)

    macd_line = [None] * len(values)
    for i in range(len(values)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = ema_fast[i] - ema_slow[i]

    # Signal line = EMA of MACD
    valid_macd = [v for v in macd_line if v is not None]
    signal = ema(valid_macd, signal_period) if len(valid_macd) >= signal_period else [None] * len(valid_macd)

    # Remap signal to original length
    signal_full = [None] * len(values)
    offset = len(values) - len(valid_macd)
    for i, v in enumerate(signal):
        signal_full[i + offset] = v

    # Histogram
    histogram = [None] * len(values)
    for i in range(len(values)):
        if macd_line[i] is not None and signal_full[i] is not None:
            histogram[i] = macd_line[i] - signal_full[i]

    return {
        "macd_line": macd_line,
        "signal_line": signal_full,
        "histogram": histogram,
    }


# ──────────────────────────────────────────────
#  Bollinger Bands
# ──────────────────────────────────────────────

def bollinger_bands(
    values: list[float], period: int = 20, std_dev: float = 2.0
) -> dict:
    """Bollinger Bands: upper, middle (SMA), lower."""
    middle = sma(values, period)
    upper = [None] * len(values)
    lower = [None] * len(values)

    for i in range(period - 1, len(values)):
        window = values[i - period + 1 : i + 1]
        mean = middle[i]
        variance = sum((x - mean) ** 2 for x in window) / period
        sd = variance ** 0.5
        upper[i] = mean + std_dev * sd
        lower[i] = mean - std_dev * sd

    return {"upper": upper, "middle": middle, "lower": lower}


# ──────────────────────────────────────────────
#  ATR
# ──────────────────────────────────────────────

def atr(bars: list[dict], period: int = 14) -> list[Optional[float]]:
    """Average True Range."""
    highs, lows, closes = _get_hlc(bars)
    result = [None] * len(bars)

    true_ranges = [highs[0] - lows[0]]  # First bar
    for i in range(1, len(bars)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        true_ranges.append(tr)

    if len(true_ranges) < period:
        return result

    # First ATR = simple average
    result[period - 1] = sum(true_ranges[:period]) / period
    for i in range(period, len(bars)):
        result[i] = (result[i - 1] * (period - 1) + true_ranges[i]) / period

    return result


# ──────────────────────────────────────────────
#  Stochastic Oscillator
# ──────────────────────────────────────────────

def stochastic(
    bars: list[dict], k_period: int = 14, d_period: int = 3
) -> dict:
    """Stochastic %K and %D."""
    highs, lows, closes = _get_hlc(bars)
    k_values = [None] * len(bars)

    for i in range(k_period - 1, len(bars)):
        h_window = highs[i - k_period + 1 : i + 1]
        l_window = lows[i - k_period + 1 : i + 1]
        highest = max(h_window)
        lowest = min(l_window)
        if highest - lowest == 0:
            k_values[i] = 50.0
        else:
            k_values[i] = ((closes[i] - lowest) / (highest - lowest)) * 100

    # %D = SMA of %K
    valid_k = [v for v in k_values if v is not None]
    d_sma = sma(valid_k, d_period) if len(valid_k) >= d_period else [None] * len(valid_k)

    d_values = [None] * len(bars)
    offset = len(bars) - len(valid_k)
    for i, v in enumerate(d_sma):
        d_values[i + offset] = v

    return {"k": k_values, "d": d_values}


# ──────────────────────────────────────────────
#  ADX
# ──────────────────────────────────────────────

def adx(bars: list[dict], period: int = 14) -> dict:
    """Average Directional Index with +DI and -DI."""
    highs, lows, closes = _get_hlc(bars)
    n = len(bars)

    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    tr_list = [0.0] * n

    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]
        plus_dm[i] = up_move if (up_move > down_move and up_move > 0) else 0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0) else 0
        tr_list[i] = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )

    # Smoothed sums
    smoothed_tr = [None] * n
    smoothed_plus = [None] * n
    smoothed_minus = [None] * n

    if n < period + 1:
        return {"adx": [None] * n, "plus_di": [None] * n, "minus_di": [None] * n}

    smoothed_tr[period] = sum(tr_list[1 : period + 1])
    smoothed_plus[period] = sum(plus_dm[1 : period + 1])
    smoothed_minus[period] = sum(minus_dm[1 : period + 1])

    for i in range(period + 1, n):
        smoothed_tr[i] = smoothed_tr[i - 1] - (smoothed_tr[i - 1] / period) + tr_list[i]
        smoothed_plus[i] = smoothed_plus[i - 1] - (smoothed_plus[i - 1] / period) + plus_dm[i]
        smoothed_minus[i] = smoothed_minus[i - 1] - (smoothed_minus[i - 1] / period) + minus_dm[i]

    plus_di = [None] * n
    minus_di = [None] * n
    dx = [None] * n

    for i in range(period, n):
        if smoothed_tr[i] and smoothed_tr[i] > 0:
            plus_di[i] = (smoothed_plus[i] / smoothed_tr[i]) * 100
            minus_di[i] = (smoothed_minus[i] / smoothed_tr[i]) * 100
            di_sum = plus_di[i] + minus_di[i]
            dx[i] = (abs(plus_di[i] - minus_di[i]) / di_sum * 100) if di_sum > 0 else 0

    # ADX = smoothed DX
    adx_values = [None] * n
    valid_dx = [(i, v) for i, v in enumerate(dx) if v is not None]
    if len(valid_dx) >= period:
        start_idx = valid_dx[period - 1][0]
        adx_values[start_idx] = sum(v for _, v in valid_dx[:period]) / period
        for j in range(period, len(valid_dx)):
            idx = valid_dx[j][0]
            prev_idx = valid_dx[j - 1][0]
            adx_values[idx] = (adx_values[prev_idx] * (period - 1) + valid_dx[j][1]) / period

    return {"adx": adx_values, "plus_di": plus_di, "minus_di": minus_di}


# ──────────────────────────────────────────────
#  Pivot Points
# ──────────────────────────────────────────────

def pivot_points(symbol: str, method: str = "classic") -> dict:
    """Compute pivot points from the previous day.

    Args:
        symbol: Trading symbol.
        method: 'classic', 'fibonacci', or 'camarilla'.

    Returns:
        dict with pivot, support, and resistance levels.
    """
    bars = mt5t.get_ohlc(symbol, "D1", 2)
    if len(bars) < 2:
        raise RuntimeError("Insufficient daily data")

    prev = bars[-2]  # Previous day
    h, l, c = prev["high"], prev["low"], prev["close"]
    pivot = (h + l + c) / 3

    if method == "classic":
        return {
            "method": "classic",
            "pivot": round(pivot, 5),
            "r1": round(2 * pivot - l, 5),
            "r2": round(pivot + (h - l), 5),
            "r3": round(h + 2 * (pivot - l), 5),
            "s1": round(2 * pivot - h, 5),
            "s2": round(pivot - (h - l), 5),
            "s3": round(l - 2 * (h - pivot), 5),
        }
    elif method == "fibonacci":
        diff = h - l
        return {
            "method": "fibonacci",
            "pivot": round(pivot, 5),
            "r1": round(pivot + 0.382 * diff, 5),
            "r2": round(pivot + 0.618 * diff, 5),
            "r3": round(pivot + 1.000 * diff, 5),
            "s1": round(pivot - 0.382 * diff, 5),
            "s2": round(pivot - 0.618 * diff, 5),
            "s3": round(pivot - 1.000 * diff, 5),
        }
    elif method == "camarilla":
        diff = h - l
        return {
            "method": "camarilla",
            "pivot": round(pivot, 5),
            "r1": round(c + diff * 1.1 / 12, 5),
            "r2": round(c + diff * 1.1 / 6, 5),
            "r3": round(c + diff * 1.1 / 4, 5),
            "r4": round(c + diff * 1.1 / 2, 5),
            "s1": round(c - diff * 1.1 / 12, 5),
            "s2": round(c - diff * 1.1 / 6, 5),
            "s3": round(c - diff * 1.1 / 4, 5),
            "s4": round(c - diff * 1.1 / 2, 5),
        }
    else:
        raise ValueError(f"Method '{method}' is not valid. Use: classic, fibonacci, camarilla")


# ──────────────────────────────────────────────
#  Full analysis
# ──────────────────────────────────────────────

def get_analysis(
    symbol: str,
    timeframe: str = "H1",
    count: int = 200,
) -> dict:
    """Perform a full technical analysis on a symbol.

    Returns:
        dict with all computed indicators and a summary.
    """
    mt5t._check_initialized()
    bars, closes = _get_closes(symbol, timeframe, count)

    # Compute indicators
    rsi_values = rsi(closes)
    macd_data = macd(closes)
    bb_data = bollinger_bands(closes)
    atr_values = atr(bars)
    stoch_data = stochastic(bars)
    adx_data = adx(bars)
    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)
    sma_200 = sma(closes, 200)
    ema_12 = ema(closes, 12)
    ema_26 = ema(closes, 26)
    tema_20 = tema(closes, 20)

    # Current values (latest available)
    current = closes[-1]
    current_rsi = rsi_values[-1]
    current_macd = macd_data["macd_line"][-1]
    current_signal = macd_data["signal_line"][-1]
    current_hist = macd_data["histogram"][-1]
    current_bb_upper = bb_data["upper"][-1]
    current_bb_lower = bb_data["lower"][-1]
    current_atr = atr_values[-1]
    current_stoch_k = stoch_data["k"][-1]
    current_stoch_d = stoch_data["d"][-1]
    current_adx = adx_data["adx"][-1]
    current_plus_di = adx_data["plus_di"][-1]
    current_minus_di = adx_data["minus_di"][-1]

    # Generate signals
    signals = []

    # RSI
    if current_rsi is not None:
        if current_rsi > 70:
            signals.append({"indicator": "RSI", "signal": "OVERBOUGHT", "value": round(current_rsi, 2)})
        elif current_rsi < 30:
            signals.append({"indicator": "RSI", "signal": "OVERSOLD", "value": round(current_rsi, 2)})
        else:
            signals.append({"indicator": "RSI", "signal": "NEUTRAL", "value": round(current_rsi, 2)})

    # MACD
    if current_macd is not None and current_signal is not None:
        if current_macd > current_signal:
            signals.append({"indicator": "MACD", "signal": "BULLISH", "value": round(current_hist, 6)})
        else:
            signals.append({"indicator": "MACD", "signal": "BEARISH", "value": round(current_hist, 6)})

    # Bollinger
    if current_bb_upper is not None:
        if current > current_bb_upper:
            signals.append({"indicator": "Bollinger", "signal": "ABOVE_UPPER", "value": round(current, 5)})
        elif current < current_bb_lower:
            signals.append({"indicator": "Bollinger", "signal": "BELOW_LOWER", "value": round(current, 5)})
        else:
            bb_pct = (current - current_bb_lower) / (current_bb_upper - current_bb_lower) * 100
            signals.append({"indicator": "Bollinger", "signal": "IN_BAND", "value": round(bb_pct, 1)})

    # Stochastic
    if current_stoch_k is not None:
        if current_stoch_k > 80:
            signals.append({"indicator": "Stochastic", "signal": "OVERBOUGHT", "value": round(current_stoch_k, 2)})
        elif current_stoch_k < 20:
            signals.append({"indicator": "Stochastic", "signal": "OVERSOLD", "value": round(current_stoch_k, 2)})

    # ADX trend strength
    if current_adx is not None:
        trend = "STRONG" if current_adx > 25 else "WEAK"
        direction = "BULLISH" if (current_plus_di or 0) > (current_minus_di or 0) else "BEARISH"
        signals.append({
            "indicator": "ADX",
            "signal": f"{trend}_TREND_{direction}",
            "value": round(current_adx, 2),
        })

    # SMA trend
    if sma_50[-1] is not None and sma_200[-1] is not None:
        if sma_50[-1] > sma_200[-1]:
            signals.append({"indicator": "SMA_Cross", "signal": "GOLDEN_CROSS", "value": "SMA50 > SMA200"})
        else:
            signals.append({"indicator": "SMA_Cross", "signal": "DEATH_CROSS", "value": "SMA50 < SMA200"})

    # Overall bias
    bullish = sum(1 for s in signals if "BULLISH" in s["signal"] or "OVERSOLD" in s["signal"] or "GOLDEN" in s["signal"])
    bearish = sum(1 for s in signals if "BEARISH" in s["signal"] or "OVERBOUGHT" in s["signal"] or "DEATH" in s["signal"])

    if bullish > bearish + 1:
        overall = "BULLISH"
    elif bearish > bullish + 1:
        overall = "BEARISH"
    else:
        overall = "NEUTRAL"

    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "current_price": current,
        "bars_analyzed": len(bars),
        "timestamp": str(bars[-1]["time"]),
        "indicators": {
            "sma_20": round(sma_20[-1], 5) if sma_20[-1] else None,
            "sma_50": round(sma_50[-1], 5) if sma_50[-1] else None,
            "sma_200": round(sma_200[-1], 5) if sma_200[-1] else None,
            "ema_12": round(ema_12[-1], 5) if ema_12[-1] else None,
            "ema_26": round(ema_26[-1], 5) if ema_26[-1] else None,
            "tema_20": round(tema_20[-1], 5) if tema_20[-1] else None,
            "rsi_14": round(current_rsi, 2) if current_rsi else None,
            "macd": round(current_macd, 6) if current_macd else None,
            "macd_signal": round(current_signal, 6) if current_signal else None,
            "macd_histogram": round(current_hist, 6) if current_hist else None,
            "bb_upper": round(current_bb_upper, 5) if current_bb_upper else None,
            "bb_middle": round(bb_data["middle"][-1], 5) if bb_data["middle"][-1] else None,
            "bb_lower": round(current_bb_lower, 5) if current_bb_lower else None,
            "atr_14": round(current_atr, 5) if current_atr else None,
            "stoch_k": round(current_stoch_k, 2) if current_stoch_k else None,
            "stoch_d": round(current_stoch_d, 2) if current_stoch_d else None,
            "adx": round(current_adx, 2) if current_adx else None,
            "plus_di": round(current_plus_di, 2) if current_plus_di else None,
            "minus_di": round(current_minus_di, 2) if current_minus_di else None,
        },
        "signals": signals,
        "overall_bias": overall,
        "bullish_signals": bullish,
        "bearish_signals": bearish,
    }


# ──────────────────────────────────────────────
#  CLI
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="MT5 Technical Indicators")
    parser.add_argument("symbol", help="Symbol (e.g. EURUSD)")
    parser.add_argument("--timeframe", default="H1", help="Timeframe (M1..MN1)")
    parser.add_argument("--count", type=int, default=200, help="Number of bars")
    parser.add_argument(
        "--indicators", nargs="+",
        choices=["sma", "ema", "tema", "rsi", "macd", "bbands", "atr", "stoch", "adx"],
        help="Specific indicators",
    )
    parser.add_argument("--analysis", action="store_true", help="Full analysis")
    parser.add_argument("--pivots", choices=["classic", "fibonacci", "camarilla"],
                        nargs="?", const="classic", help="Pivot points")

    args = parser.parse_args()

    try:
        if args.analysis:
            result = get_analysis(args.symbol, args.timeframe, args.count)
        elif args.pivots:
            result = pivot_points(args.symbol, args.pivots)
        else:
            bars, closes = _get_closes(args.symbol, args.timeframe, args.count)
            result = {"symbol": args.symbol, "timeframe": args.timeframe}

            indicators = args.indicators or ["rsi", "macd", "bbands", "atr"]

            if "sma" in indicators:
                result["sma_20"] = round(sma(closes, 20)[-1] or 0, 5)
                result["sma_50"] = round(sma(closes, 50)[-1] or 0, 5)
            if "ema" in indicators:
                result["ema_12"] = round(ema(closes, 12)[-1] or 0, 5)
                result["ema_26"] = round(ema(closes, 26)[-1] or 0, 5)
            if "tema" in indicators:
                result["tema_20"] = round(tema(closes, 20)[-1] or 0, 5)
            if "rsi" in indicators:
                result["rsi_14"] = round(rsi(closes)[-1] or 0, 2)
            if "macd" in indicators:
                m = macd(closes)
                result["macd"] = round(m["macd_line"][-1] or 0, 6)
                result["macd_signal"] = round(m["signal_line"][-1] or 0, 6)
                result["macd_histogram"] = round(m["histogram"][-1] or 0, 6)
            if "bbands" in indicators:
                bb = bollinger_bands(closes)
                result["bb_upper"] = round(bb["upper"][-1] or 0, 5)
                result["bb_lower"] = round(bb["lower"][-1] or 0, 5)
            if "atr" in indicators:
                result["atr_14"] = round(atr(bars)[-1] or 0, 5)
            if "stoch" in indicators:
                s = stochastic(bars)
                result["stoch_k"] = round(s["k"][-1] or 0, 2)
                result["stoch_d"] = round(s["d"][-1] or 0, 2)
            if "adx" in indicators:
                a = adx(bars)
                result["adx"] = round(a["adx"][-1] or 0, 2)

        print(json.dumps(result, indent=2, default=str, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
