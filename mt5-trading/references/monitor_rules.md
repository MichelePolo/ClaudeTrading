# MT5 Monitor Rules

Complete documentation of all rules supported by `mt5_monitor.py`.

## Config Structure

```json
{
  "description": "Optional description",
  "interval_seconds": 30,
  "max_cycles": 0,
  "log_file": "mt5_monitor_log.json",
  "rules": [ ... ]
}
```

Global parameters:

- `interval_seconds`: pause between cycles (default: 30)
- `max_cycles`: maximum number of cycles, 0 = infinite (default: 0)
- `log_file`: JSON log file path (default: mt5_monitor_log.json)

## Rules

Every rule is a JSON object with at least `name`, `type`, `enabled`.

---

### `trailing_stop` — Automatic Trailing Stop

Moves the SL following the price on all profitable positions.

```json
{
  "name": "Global trailing 20 pips",
  "type": "trailing_stop",
  "enabled": true,
  "trail_points": 200,
  "symbol": "EURUSD",
  "magic": 1001
}
```

| Parameter | Type | Required | Description |
|-----------|------|:---:|-------------|
| `trail_points` | float | Yes | Trailing distance in points |
| `symbol` | string | No | Filter by symbol |
| `magic` | int | No | Filter by magic number |

---

### `breakeven` — Move to Break-Even

Moves the SL to the opening price when profit exceeds a threshold.

```json
{
  "name": "BE on EURUSD after 15 pips",
  "type": "breakeven",
  "enabled": true,
  "symbol": "EURUSD",
  "min_profit_points": 150,
  "offset_points": 5
}
```

| Parameter | Type | Required | Description |
|-----------|------|:---:|-------------|
| `min_profit_points` | float | Yes | Minimum profit in points to activate BE |
| `offset_points` | float | No | Extra points beyond BE (default: 5) |
| `symbol` | string | No | Filter by symbol |

---

### `price_alert` — Price Level Alert

Notifies (and optionally executes an action) when price reaches a level.

```json
{
  "name": "Breakout 1.1000",
  "type": "price_alert",
  "enabled": true,
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

| Parameter | Type | Required | Description |
|-----------|------|:---:|-------------|
| `symbol` | string | Yes | Symbol to monitor |
| `level` | float | Yes | Price level |
| `direction` | string | No | `"above"` or `"below"` (default: above) |
| `notify_desktop` | bool | No | Windows desktop notification (default: false) |
| `action` | object | No | Action to execute (strategy_executor format) |

The alert is triggered **only once** per session.

---

### `close_on_profit` — Close on Target Profit

Closes positions that reach a profit target in account currency.

```json
{
  "name": "TP at 50 EUR",
  "type": "close_on_profit",
  "enabled": true,
  "target_profit": 50.0,
  "symbol": "EURUSD",
  "magic": 1001
}
```

| Parameter | Type | Required | Description |
|-----------|------|:---:|-------------|
| `target_profit` | float | Yes | Target profit in account currency |
| `symbol` | string | No | Filter by symbol |
| `magic` | int | No | Filter by magic number |

---

### `close_on_loss` — Close on Maximum Loss

Closes positions that exceed a maximum loss.

```json
{
  "name": "Max loss 30 EUR",
  "type": "close_on_loss",
  "enabled": true,
  "max_loss": 30.0,
  "symbol": "EURUSD"
}
```

| Parameter | Type | Required | Description |
|-----------|------|:---:|-------------|
| `max_loss` | float | Yes | Maximum loss in account currency (positive value) |
| `symbol` | string | No | Filter by symbol |

---

### `close_on_time` — Close at Time

Closes positions after a certain time (PC local time).

```json
{
  "name": "Evening close",
  "type": "close_on_time",
  "enabled": true,
  "close_after": "21:30",
  "symbol": "EURUSD",
  "magic": 1001
}
```

| Parameter | Type | Required | Description |
|-----------|------|:---:|-------------|
| `close_after` | string | Yes | Time in "HH:MM" format |
| `symbol` | string | No | Filter by symbol |
| `magic` | int | No | Filter by magic number |

---

### `indicator_alert` — Technical Indicator Alert

Alerts based on indicator conditions (requires `mt5_indicators.py`).

```json
{
  "name": "RSI overbought EURUSD",
  "type": "indicator_alert",
  "enabled": true,
  "symbol": "EURUSD",
  "timeframe": "H1",
  "indicator": "rsi_overbought",
  "threshold": 75,
  "notify_desktop": true,
  "action": {
    "action": "sell",
    "symbol": "EURUSD",
    "volume": 0.05,
    "sl": 1.1050,
    "tp": 1.0900
  }
}
```

| Parameter | Type | Required | Description |
|-----------|------|:---:|-------------|
| `symbol` | string | Yes | Symbol |
| `indicator` | string | Yes | Indicator type (see below) |
| `timeframe` | string | No | Timeframe (default: H1) |
| `threshold` | float | No | Threshold for RSI (default: 70/30) |
| `notify_desktop` | bool | No | Desktop notification |
| `action` | object | No | Action to execute |

Supported indicators:

- `rsi_overbought` — RSI above threshold (default 70)
- `rsi_oversold` — RSI below threshold (default 30)
- `macd_bullish_cross` — Positive MACD histogram
- `macd_bearish_cross` — Negative MACD histogram
- `bb_upper_breakout` — Price above Bollinger upper
- `bb_lower_breakout` — Price below Bollinger lower

---

### `tema_price_cross` — TEMA/Price Crossover

Opens a trade when the price crosses above or below the TEMA (Triple Exponential Moving Average). Optionally closes the opposite position before opening.

```json
{
  "name": "TEMA cross EURUSD H1",
  "type": "tema_price_cross",
  "enabled": true,
  "symbol": "EURUSD",
  "timeframe": "H1",
  "tema_period": 20,
  "volume": 0.01,
  "sl_points": 200,
  "tp_points": 400,
  "magic": 1001,
  "close_opposite": true,
  "comment": "tema_cross_h1"
}
```

| Parameter | Type | Required | Description |
|-----------|------|:---:|-------------|
| `symbol` | string | Yes | Symbol to monitor |
| `timeframe` | string | No | Timeframe (default: H1) |
| `tema_period` | int | No | TEMA period (default: 20) |
| `volume` | float | No | Lot size (default: 0.01) |
| `sl_points` | float | No | Stop-loss in points (default: 0 = no SL) |
| `tp_points` | float | No | Take-profit in points (default: 0 = no TP) |
| `magic` | int | No | Magic number (default: 0) |
| `close_opposite` | bool | No | Close existing opposite position before opening (default: true) |
| `comment` | string | No | Order comment |

Crossover logic:
- **BUY**: previous close <= previous TEMA, current close > current TEMA
- **SELL**: previous close >= previous TEMA, current close < current TEMA

---

### `max_drawdown` — Account Drawdown Protection

Closes ALL positions if account drawdown exceeds a percentage.

```json
{
  "name": "Drawdown protection 5%",
  "type": "max_drawdown",
  "enabled": true,
  "max_drawdown_percent": 5.0,
  "close_all": true
}
```

| Parameter | Type | Required | Description |
|-----------|------|:---:|-------------|
| `max_drawdown_percent` | float | Yes | Maximum drawdown percentage |
| `close_all` | bool | No | If true, closes all positions (default: false = alert only) |

---

## Complete Configuration Examples

### Conservative Day Trader

```json
{
  "description": "Day trading with automatic protections",
  "interval_seconds": 15,
  "rules": [
    {
      "name": "Trailing 15 pips",
      "type": "trailing_stop",
      "enabled": true,
      "trail_points": 150
    },
    {
      "name": "Break-even after 10 pips",
      "type": "breakeven",
      "enabled": true,
      "min_profit_points": 100,
      "offset_points": 5
    },
    {
      "name": "Evening close",
      "type": "close_on_time",
      "enabled": true,
      "close_after": "21:00"
    },
    {
      "name": "Max drawdown 3%",
      "type": "max_drawdown",
      "enabled": true,
      "max_drawdown_percent": 3.0,
      "close_all": true
    }
  ]
}
```

### Aggressive Scalper

```json
{
  "description": "Scalping with fixed targets and fast protection",
  "interval_seconds": 5,
  "rules": [
    {
      "name": "TP at 20 EUR",
      "type": "close_on_profit",
      "enabled": true,
      "target_profit": 20.0
    },
    {
      "name": "SL at 10 EUR",
      "type": "close_on_loss",
      "enabled": true,
      "max_loss": 10.0
    },
    {
      "name": "Fast BE",
      "type": "breakeven",
      "enabled": true,
      "min_profit_points": 50,
      "offset_points": 3
    },
    {
      "name": "Max drawdown 2%",
      "type": "max_drawdown",
      "enabled": true,
      "max_drawdown_percent": 2.0,
      "close_all": true
    }
  ]
}
```

### Swing Trader with Indicator Alerts

```json
{
  "description": "Swing with technical alerts and wide trailing",
  "interval_seconds": 60,
  "rules": [
    {
      "name": "Trailing 50 pips",
      "type": "trailing_stop",
      "enabled": true,
      "trail_points": 500
    },
    {
      "name": "RSI overbought EURUSD",
      "type": "indicator_alert",
      "enabled": true,
      "symbol": "EURUSD",
      "indicator": "rsi_overbought",
      "threshold": 75,
      "notify_desktop": true
    },
    {
      "name": "MACD bearish GBPUSD",
      "type": "indicator_alert",
      "enabled": true,
      "symbol": "GBPUSD",
      "indicator": "macd_bearish_cross",
      "notify_desktop": true
    },
    {
      "name": "Max drawdown 5%",
      "type": "max_drawdown",
      "enabled": true,
      "max_drawdown_percent": 5.0,
      "close_all": true
    }
  ]
}
```
