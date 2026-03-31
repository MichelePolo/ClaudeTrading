# MT5 Strategy JSON Format

This document describes the JSON format that Claude must generate to execute trading strategies on MetaTrader 5.

## Base Structure

```json
{
  "description": "Strategy description",
  "risk_rules": {
    "max_risk_per_trade": 1.0,
    "max_open_positions": 5,
    "max_daily_loss_percent": 3.0
  },
  "actions": [
    { "action": "connect" },
    { "action": "buy", "symbol": "EURUSD", "volume": 0.1, "sl": 1.0800, "tp": 1.1000 },
    { "action": "disconnect" }
  ]
}
```

## Available Actions

### Connection
```json
{ "action": "connect" }
{ "action": "connect", "login": 12345, "password": "xxx", "server": "BrokerName-Demo" }
{ "action": "disconnect" }
```

### Information
```json
{ "action": "account_info" }
{ "action": "symbol_info", "symbol": "EURUSD" }
{ "action": "get_tick", "symbol": "EURUSD" }
{ "action": "get_ohlc", "symbol": "EURUSD", "timeframe": "H1", "count": 50 }
{ "action": "get_positions" }
{ "action": "get_positions", "symbol": "EURUSD", "magic": 1001 }
{ "action": "get_pending_orders" }
```

### Market Orders
```json
{
  "action": "buy",
  "symbol": "EURUSD",
  "volume": 0.1,
  "sl": 1.0800,
  "tp": 1.1000,
  "magic": 1001,
  "comment": "Breakout strategy"
}

{
  "action": "sell",
  "symbol": "GBPUSD",
  "volume": 0.05,
  "sl": 1.2800,
  "tp": 1.2600
}
```

### Pending Orders
```json
{
  "action": "pending_order",
  "symbol": "EURUSD",
  "order_type": "BUY_LIMIT",
  "volume": 0.1,
  "price": 1.0850,
  "sl": 1.0800,
  "tp": 1.0950,
  "magic": 1001
}
```
Types: `BUY_LIMIT`, `SELL_LIMIT`, `BUY_STOP`, `SELL_STOP`

### Close Positions
```json
{ "action": "close", "ticket": 123456 }
{ "action": "close", "ticket": 123456, "volume": 0.05 }
{ "action": "close_all" }
{ "action": "close_all", "symbol": "EURUSD" }
{ "action": "close_all", "magic": 1001 }
```

### Cancel Pending Orders
```json
{ "action": "cancel", "ticket": 789012 }
{ "action": "cancel_all" }
{ "action": "cancel_all", "symbol": "EURUSD" }
```

### Modify
```json
{ "action": "modify", "ticket": 123456, "sl": 1.0850, "tp": 1.1050 }
{ "action": "modify_pending", "ticket": 789012, "price": 1.0840, "sl": 1.0790 }
```

### Risk Management
```json
{ "action": "trailing_stop", "ticket": 123456, "trail_points": 200 }
{ "action": "breakeven", "ticket": 123456, "offset_points": 10 }
{ "action": "calculate_lot", "symbol": "EURUSD", "risk_percent": 1.0, "sl_points": 500 }
```

### Utility
```json
{ "action": "wait", "seconds": 2 }
```

## Special Action Flags

- `"stop_on_error": true` — stops strategy execution if this action fails.

## Complete Strategy Examples

### Strategy: Breakout with Controlled Risk
```json
{
  "description": "EURUSD breakout above 1.1000 with 1% risk",
  "actions": [
    { "action": "connect", "stop_on_error": true },
    { "action": "account_info" },
    { "action": "calculate_lot", "symbol": "EURUSD", "risk_percent": 1.0, "sl_points": 300 },
    {
      "action": "pending_order",
      "symbol": "EURUSD",
      "order_type": "BUY_STOP",
      "volume": 0.1,
      "price": 1.1000,
      "sl": 1.0970,
      "tp": 1.1060,
      "magic": 2001,
      "comment": "breakout_long"
    }
  ]
}
```

### Strategy: Close All and Reposition
```json
{
  "description": "Close EURUSD positions and open sell with trailing",
  "actions": [
    { "action": "connect", "stop_on_error": true },
    { "action": "close_all", "symbol": "EURUSD" },
    { "action": "wait", "seconds": 1 },
    {
      "action": "sell",
      "symbol": "EURUSD",
      "volume": 0.1,
      "sl": 1.1050,
      "tp": 1.0900,
      "magic": 3001
    }
  ]
}
```

### Strategy: Manage Active Positions
```json
{
  "description": "Move all profitable positions to break-even",
  "actions": [
    { "action": "connect", "stop_on_error": true },
    { "action": "get_positions" },
    { "action": "breakeven", "ticket": 123456, "offset_points": 5 },
    { "action": "trailing_stop", "ticket": 123456, "trail_points": 150 }
  ]
}
```
