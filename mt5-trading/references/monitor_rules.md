# Regole di Monitoraggio MT5

Documentazione completa di tutte le regole supportate da `mt5_monitor.py`.

## Struttura config

```json
{
  "description": "Descrizione opzionale",
  "interval_seconds": 30,
  "max_cycles": 0,
  "log_file": "mt5_monitor_log.json",
  "rules": [ ... ]
}
```

Parametri globali:
- `interval_seconds`: pausa tra un ciclo e l'altro (default: 30)
- `max_cycles`: numero massimo di cicli, 0 = infinito (default: 0)
- `log_file`: percorso file di log JSON (default: mt5_monitor_log.json)

## Regole

Ogni regola è un oggetto JSON con almeno `name`, `type`, `enabled`.

---

### `trailing_stop` — Trailing stop automatico

Sposta lo SL seguendo il prezzo su tutte le posizioni in profitto.

```json
{
  "name": "Trailing globale 20 pips",
  "type": "trailing_stop",
  "enabled": true,
  "trail_points": 200,
  "symbol": "EURUSD",
  "magic": 1001
}
```

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `trail_points` | float | ✅ | Distanza trailing in punti |
| `symbol` | string | ❌ | Filtra per simbolo |
| `magic` | int | ❌ | Filtra per magic number |

---

### `breakeven` — Sposta a break-even

Sposta lo SL al prezzo di apertura quando il profitto supera una soglia.

```json
{
  "name": "BE su EURUSD dopo 15 pips",
  "type": "breakeven",
  "enabled": true,
  "symbol": "EURUSD",
  "min_profit_points": 150,
  "offset_points": 5
}
```

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `min_profit_points` | float | ✅ | Profitto minimo in punti per attivare il BE |
| `offset_points` | float | ❌ | Punti extra oltre il BE (default: 5) |
| `symbol` | string | ❌ | Filtra per simbolo |

---

### `price_alert` — Alert su livello di prezzo

Notifica (e opzionalmente esegue un'azione) quando il prezzo raggiunge un livello.

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

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `symbol` | string | ✅ | Simbolo da monitorare |
| `level` | float | ✅ | Livello di prezzo |
| `direction` | string | ❌ | `"above"` o `"below"` (default: above) |
| `notify_desktop` | bool | ❌ | Notifica desktop Windows (default: false) |
| `action` | object | ❌ | Azione da eseguire (formato strategy_executor) |

L'alert viene notificato **una sola volta** per sessione.

---

### `close_on_profit` — Chiudi su profitto target

Chiude posizioni che raggiungono un profitto in valuta account.

```json
{
  "name": "TP a 50 EUR",
  "type": "close_on_profit",
  "enabled": true,
  "target_profit": 50.0,
  "symbol": "EURUSD",
  "magic": 1001
}
```

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `target_profit` | float | ✅ | Profitto target in valuta account |
| `symbol` | string | ❌ | Filtra per simbolo |
| `magic` | int | ❌ | Filtra per magic number |

---

### `close_on_loss` — Chiudi su perdita massima

Chiude posizioni che superano una perdita massima.

```json
{
  "name": "Max loss 30 EUR",
  "type": "close_on_loss",
  "enabled": true,
  "max_loss": 30.0,
  "symbol": "EURUSD"
}
```

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `max_loss` | float | ✅ | Perdita massima in valuta account (valore positivo) |
| `symbol` | string | ❌ | Filtra per simbolo |

---

### `close_on_time` — Chiudi a orario

Chiude posizioni dopo un certo orario (ora locale del PC).

```json
{
  "name": "Chiusura serale",
  "type": "close_on_time",
  "enabled": true,
  "close_after": "21:30",
  "symbol": "EURUSD",
  "magic": 1001
}
```

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `close_after` | string | ✅ | Orario formato "HH:MM" |
| `symbol` | string | ❌ | Filtra per simbolo |
| `magic` | int | ❌ | Filtra per magic number |

---

### `indicator_alert` — Alert su indicatori tecnici

Alert basati su condizioni degli indicatori (richiede `mt5_indicators.py`).

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

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `symbol` | string | ✅ | Simbolo |
| `indicator` | string | ✅ | Tipo indicatore (vedi sotto) |
| `timeframe` | string | ❌ | Timeframe (default: H1) |
| `threshold` | float | ❌ | Soglia per RSI (default: 70/30) |
| `notify_desktop` | bool | ❌ | Notifica desktop |
| `action` | object | ❌ | Azione da eseguire |

Indicatori supportati:
- `rsi_overbought` — RSI sopra threshold (default 70)
- `rsi_oversold` — RSI sotto threshold (default 30)
- `macd_bullish_cross` — Istogramma MACD positivo
- `macd_bearish_cross` — Istogramma MACD negativo
- `bb_upper_breakout` — Prezzo sopra Bollinger upper
- `bb_lower_breakout` — Prezzo sotto Bollinger lower

---

### `max_drawdown` — Protezione drawdown account

Chiude TUTTE le posizioni se il drawdown dell'account supera una percentuale.

```json
{
  "name": "Protezione drawdown 5%",
  "type": "max_drawdown",
  "enabled": true,
  "max_drawdown_percent": 5.0,
  "close_all": true
}
```

| Parametro | Tipo | Obbligatorio | Descrizione |
|-----------|------|:---:|-------------|
| `max_drawdown_percent` | float | ✅ | Percentuale massima di drawdown |
| `close_all` | bool | ❌ | Se true, chiude tutte le posizioni (default: false = solo alert) |

---

## Esempi di configurazioni complete

### Day trader conservativo

```json
{
  "description": "Day trading con protezioni automatiche",
  "interval_seconds": 15,
  "rules": [
    {
      "name": "Trailing 15 pips",
      "type": "trailing_stop",
      "enabled": true,
      "trail_points": 150
    },
    {
      "name": "Break-even dopo 10 pips",
      "type": "breakeven",
      "enabled": true,
      "min_profit_points": 100,
      "offset_points": 5
    },
    {
      "name": "Chiusura serale",
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

### Scalper aggressivo

```json
{
  "description": "Scalping con target fissi e protezione rapida",
  "interval_seconds": 5,
  "rules": [
    {
      "name": "TP a 20 EUR",
      "type": "close_on_profit",
      "enabled": true,
      "target_profit": 20.0
    },
    {
      "name": "SL a 10 EUR",
      "type": "close_on_loss",
      "enabled": true,
      "max_loss": 10.0
    },
    {
      "name": "BE rapido",
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

### Swing trader con alert indicatori

```json
{
  "description": "Swing con alert tecnici e trailing ampio",
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
