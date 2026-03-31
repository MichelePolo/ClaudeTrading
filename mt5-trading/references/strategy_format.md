# Formato JSON Strategia MT5

Questo documento descrive il formato JSON che Claude deve generare per eseguire strategie di trading su MetaTrader 5.

## Struttura base

```json
{
  "description": "Descrizione della strategia",
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

## Azioni disponibili

### Connessione
```json
{ "action": "connect" }
{ "action": "connect", "login": 12345, "password": "xxx", "server": "BrokerName-Demo" }
{ "action": "disconnect" }
```

### Informazioni
```json
{ "action": "account_info" }
{ "action": "symbol_info", "symbol": "EURUSD" }
{ "action": "get_tick", "symbol": "EURUSD" }
{ "action": "get_ohlc", "symbol": "EURUSD", "timeframe": "H1", "count": 50 }
{ "action": "get_positions" }
{ "action": "get_positions", "symbol": "EURUSD", "magic": 1001 }
{ "action": "get_pending_orders" }
```

### Ordini a mercato
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

### Ordini pendenti
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
Tipi: `BUY_LIMIT`, `SELL_LIMIT`, `BUY_STOP`, `SELL_STOP`

### Chiusura
```json
{ "action": "close", "ticket": 123456 }
{ "action": "close", "ticket": 123456, "volume": 0.05 }
{ "action": "close_all" }
{ "action": "close_all", "symbol": "EURUSD" }
{ "action": "close_all", "magic": 1001 }
```

### Cancellazione ordini pendenti
```json
{ "action": "cancel", "ticket": 789012 }
{ "action": "cancel_all" }
{ "action": "cancel_all", "symbol": "EURUSD" }
```

### Modifica
```json
{ "action": "modify", "ticket": 123456, "sl": 1.0850, "tp": 1.1050 }
{ "action": "modify_pending", "ticket": 789012, "price": 1.0840, "sl": 1.0790 }
```

### Gestione rischio
```json
{ "action": "trailing_stop", "ticket": 123456, "trail_points": 200 }
{ "action": "breakeven", "ticket": 123456, "offset_points": 10 }
{ "action": "calculate_lot", "symbol": "EURUSD", "risk_percent": 1.0, "sl_points": 500 }
```

### Utility
```json
{ "action": "wait", "seconds": 2 }
```

## Flag speciali per azione

- `"stop_on_error": true` — interrompe l'esecuzione della strategia se questa azione fallisce.

## Esempi di strategie complete

### Strategia: Breakout con rischio controllato
```json
{
  "description": "Breakout EURUSD sopra 1.1000 con rischio 1%",
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

### Strategia: Chiudi tutto e riposiziona
```json
{
  "description": "Chiudi posizioni EURUSD e apri sell con trailing",
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

### Strategia: Gestione posizioni attive
```json
{
  "description": "Sposta tutte le posizioni in profitto a break-even",
  "actions": [
    { "action": "connect", "stop_on_error": true },
    { "action": "get_positions" },
    { "action": "breakeven", "ticket": 123456, "offset_points": 5 },
    { "action": "trailing_stop", "ticket": 123456, "trail_points": 150 }
  ]
}
```
