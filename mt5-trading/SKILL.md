---
name: mt5-trading
description: >
  Controlla MetaTrader 5 direttamente da Claude: apri, chiudi, modifica trade, gestisci ordini
  pendenti, calcola lotti, applica trailing stop e break-even. Usa questa skill OGNI VOLTA che
  l'utente menziona trading, MetaTrader, MT5, forex, apertura/chiusura posizioni, stop loss,
  take profit, ordini, lotti, rischio percentuale, trailing stop, break-even, o descrive una
  strategia di trading da eseguire. Anche se l'utente non dice esplicitamente "MT5", se parla
  di trading su coppie valutarie, indici, materie prime, o descrive regole di entrata/uscita
  dal mercato, questa skill è quella giusta.
---

# MT5 Trading Skill

Questa skill permette a Claude di operare come trader assistant su MetaTrader 5, eseguendo
operazioni reali sul conto dell'utente tramite una libreria Python locale.

## Architettura

```
mt5-trading/
├── SKILL.md                          ← Questo file (istruzioni per Claude)
├── scripts/
│   ├── mt5_trading.py                ← Libreria Python + CLI per MT5
│   ├── mt5_strategy_executor.py      ← Esecutore di strategie JSON
│   ├── mt5_indicators.py             ← Indicatori tecnici (RSI, MACD, BB, ATR, ADX...)
│   └── mt5_monitor.py                ← Monitoraggio continuo con regole automatiche
└── references/
    ├── strategy_format.md            ← Formato JSON delle strategie
    └── monitor_rules.md              ← Documentazione regole di monitoraggio
```

## Prerequisiti (PC dell'utente)

1. **Windows** con MetaTrader 5 installato e avviato
2. **Python 3.9+** con il pacchetto `MetaTrader5`:
   ```
   pip install MetaTrader5
   ```
3. I file `mt5_trading.py` e `mt5_strategy_executor.py` copiati sul PC
4. Il terminale MT5 deve essere aperto e loggato su un account (demo o reale)

> **IMPORTANTE**: Questi script girano sul PC dell'utente, NON nel sandbox di Claude.
> Claude genera i comandi/strategie, l'utente li esegue localmente.

## Come Claude deve operare

### Flusso standard

1. **L'utente descrive cosa vuole fare** (in linguaggio naturale)
2. **Claude traduce in comandi** usando la libreria `mt5_trading.py`
3. **Claude presenta i comandi** pronti per essere eseguiti dall'utente
4. **L'utente copia ed esegue** sul proprio PC

### Due modalità di output

#### Modalità A — Comandi CLI singoli
Per operazioni semplici e dirette. Claude fornisce comandi `python mt5_trading.py ...`

Esempi:
```bash
# Connetti
python mt5_trading.py connect

# Vedi account
python mt5_trading.py account

# Compra 0.1 lotti EURUSD con SL e TP
python mt5_trading.py buy EURUSD 0.1 --sl 1.0800 --tp 1.1000 --magic 1001

# Chiudi posizione
python mt5_trading.py close 123456

# Trailing stop
python mt5_trading.py trailing 123456 200

# Calcola lotto per 1% di rischio con SL a 300 punti
python mt5_trading.py lot_size EURUSD 1.0 300
```

#### Modalità B — Strategia JSON
Per operazioni complesse e multi-step. Claude genera un JSON e fornisce il comando
per eseguirlo tramite `mt5_strategy_executor.py`.

```bash
# Salva il JSON in un file
# Poi esegui:
python mt5_strategy_executor.py strategia.json

# Oppure inline:
python mt5_strategy_executor.py --inline '{ "actions": [...] }'
```

Per il formato JSON completo, consulta: `references/strategy_format.md`

## Regole fondamentali per Claude

### Sicurezza e conferma

1. **MAI eseguire automaticamente** — Claude genera comandi, l'utente esegue
2. **Sempre chiedere conferma** prima di generare ordini a mercato
3. **Mostrare sempre un riepilogo** prima dell'esecuzione:
   - Simbolo, direzione, volume
   - Stop loss e take profit (in prezzo E in pips/punti)
   - Rischio stimato in valuta e percentuale
4. **Avvisare esplicitamente** se mancano SL o TP
5. **Suggerire sempre l'uso di account demo** per test

### Gestione del rischio

Claude deve SEMPRE considerare il rischio:

- Se l'utente non specifica il volume, **calcolare il lotto** in base al rischio
  (default: 1% del saldo per trade, salvo indicazioni diverse)
- Se l'utente non specifica SL, **chiedere sempre** prima di procedere
- Se il rischio supera il 2% per singolo trade, **avvisare** esplicitamente
- Tenere traccia delle posizioni aperte nella conversazione

### Traduzione della strategia dell'utente

Quando l'utente descrive una strategia in linguaggio naturale, Claude deve:

1. **Ripetere la strategia** in modo strutturato per conferma
2. **Identificare**: condizioni di entrata, uscita, gestione rischio
3. **Tradurre** in azioni JSON o comandi CLI
4. **Evidenziare** eventuali ambiguità o rischi
5. **Proporre** miglioramenti (es. trailing stop se manca gestione attiva)

### Esempio di conversazione tipo

**Utente**: "Voglio comprare EURUSD se rompe 1.1000, con stop a 30 pips e target 60 pips.
Rischio 1% del conto."

**Claude deve**:
1. Confermare la strategia:
   - Entry: BUY_STOP a 1.1000
   - SL: 1.0970 (30 pips sotto)
   - TP: 1.1060 (60 pips sopra)
   - Risk: 1% del saldo
2. Generare prima il calcolo del lotto:
   ```bash
   python mt5_trading.py lot_size EURUSD 1.0 300
   ```
3. Poi l'ordine pendente (dopo aver il lotto):
   ```bash
   python mt5_trading.py pending_order EURUSD BUY_STOP [LOTTO] 1.1000 --sl 1.0970 --tp 1.1060 --magic 1001 --comment "breakout_long"
   ```

## Comandi CLI disponibili (riferimento rapido)

| Comando | Descrizione |
|---------|-------------|
| `connect` | Connetti a MT5 |
| `disconnect` | Disconnetti |
| `account` | Info account (saldo, equity, margine) |
| `symbol EURUSD` | Info simbolo (spread, digits, volumi) |
| `tick EURUSD` | Ultimo prezzo bid/ask |
| `ohlc EURUSD --timeframe H1 --count 20` | Candele OHLC |
| `positions` | Posizioni aperte |
| `pending` | Ordini pendenti |
| `buy EURUSD 0.1 --sl X --tp Y` | Ordine BUY a mercato |
| `sell EURUSD 0.1 --sl X --tp Y` | Ordine SELL a mercato |
| `pending_order EURUSD BUY_LIMIT 0.1 1.0850 --sl X --tp Y` | Ordine pendente |
| `close 123456` | Chiudi posizione (totale) |
| `close 123456 --volume 0.05` | Chiusura parziale |
| `close_all` | Chiudi tutto |
| `close_all --symbol EURUSD` | Chiudi tutto su simbolo |
| `cancel 789012` | Cancella ordine pendente |
| `cancel_all` | Cancella tutti i pendenti |
| `modify 123456 --sl 1.0850 --tp 1.1050` | Modifica SL/TP |
| `modify_pending 789012 --price 1.0840` | Modifica ordine pendente |
| `trailing 123456 200` | Trailing stop (200 punti) |
| `breakeven 123456 --offset 10` | Sposta SL a break-even |
| `lot_size EURUSD 1.0 300` | Calcola lotto (1% rischio, 300pt SL) |

Ogni comando stampa il risultato in JSON. Prefisso sempre con:
```
python mt5_trading.py <comando>
```

## Quando usare Modalità A vs B

- **Modalità A (CLI)**: operazioni singole, query informative, modifiche rapide
- **Modalità B (JSON strategy)**: strategie multi-step, setup complessi con più ordini,
  sequenze che richiedono coordinazione (es. chiudi tutto → aspetta → riapri)

## Conversione pips ↔ punti

- Forex 5 digits (es. EURUSD): 1 pip = 10 punti. Quindi 30 pips = 300 punti
- Forex 3 digits (es. USDJPY): 1 pip = 10 punti. Quindi 30 pips = 300 punti
- Indici/metalli: dipende dal simbolo, Claude deve sempre verificare con `symbol_info`
- **IMPORTANTE**: la libreria lavora in punti. Claude deve convertire se l'utente parla in pips.

## Errori comuni e soluzioni

| Errore | Causa | Soluzione |
|--------|-------|-----------|
| `MT5 non inizializzato` | Terminale non avviato | `python mt5_trading.py connect` |
| `Simbolo non trovato` | Simbolo non disponibile | Verificare nome esatto col broker |
| `Volume non valido` | Lotto fuori range | Controllare con `symbol_info` i limiti |
| `Ordine rifiutato [10013]` | Mercato chiuso | Verificare orari di trading |
| `Ordine rifiutato [10016]` | SL/TP non valido | SL/TP troppo vicino al prezzo |
| `Margine insufficiente` | Fondi insufficienti | Ridurre volume o chiudere posizioni |

## Modalità C — Analisi tecnica con indicatori

Lo script `mt5_indicators.py` fornisce indicatori tecnici calcolati direttamente sui dati MT5.
Claude deve usarlo PRIMA di suggerire trade, per supportare le decisioni con dati oggettivi.

### Comandi indicatori

```bash
# Analisi completa (tutti gli indicatori + segnali + bias)
python mt5_indicators.py EURUSD --analysis

# Indicatori specifici
python mt5_indicators.py EURUSD --indicators rsi macd bbands atr

# Pivot points giornalieri
python mt5_indicators.py EURUSD --pivots classic
python mt5_indicators.py EURUSD --pivots fibonacci
python mt5_indicators.py EURUSD --pivots camarilla

# Timeframe diverso
python mt5_indicators.py XAUUSD --analysis --timeframe M15
```

### Indicatori disponibili

| Indicatore | Chiave CLI | Output |
|-----------|-----------|--------|
| SMA (20, 50, 200) | `sma` | Medie mobili semplici |
| EMA (12, 26) | `ema` | Medie mobili esponenziali |
| RSI (14) | `rsi` | Indice forza relativa (0-100) |
| MACD (12,26,9) | `macd` | Linea, segnale, istogramma |
| Bollinger Bands (20,2) | `bbands` | Upper, middle, lower |
| ATR (14) | `atr` | Volatilità media |
| Stochastic (14,3) | `stoch` | %K e %D (0-100) |
| ADX (14) | `adx` | Forza trend + DI+/DI- |
| Pivot Points | `--pivots` | Classic, Fibonacci, Camarilla |

### Come Claude usa l'analisi

L'output di `--analysis` include un campo `overall_bias` (BULLISH / BEARISH / NEUTRAL) e
una lista `signals` con ogni indicatore e il suo segnale. Claude deve:

1. **Eseguire l'analisi** prima di proporre un trade
2. **Citare gli indicatori** che supportano la decisione
3. **Avvisare** se i segnali sono contrastanti
4. **Usare l'ATR** per calcolare SL/TP proporzionati alla volatilità

Esempio di workflow per Claude:
- Utente: "Cosa ne pensi di un long su EURUSD?"
- Claude genera: `python mt5_indicators.py EURUSD --analysis`
- Claude legge il JSON e risponde: "RSI a 45 (neutro), MACD bullish, prezzo sopra SMA200.
  Bias complessivo: moderatamente bullish. ATR a 80 punti, suggerisco SL a 120pt e TP a 160pt."

## Modalità D — Monitoraggio continuo

Lo script `mt5_monitor.py` gira in loop sul PC dell'utente e applica regole automatiche.
Claude genera la configurazione JSON, l'utente la esegue.

### Comandi monitor

```bash
# Genera una config di esempio
python mt5_monitor.py --generate-config

# Avvia il monitor
python mt5_monitor.py mt5_monitor_config.json

# Modalità simulazione (non esegue azioni reali)
python mt5_monitor.py mt5_monitor_config.json --dry-run

# Override intervallo
python mt5_monitor.py mt5_monitor_config.json --interval 10
```

### Tipi di regole disponibili

| Tipo | Descrizione |
|------|-------------|
| `trailing_stop` | Trailing stop automatico su posizioni in profitto |
| `breakeven` | Sposta SL a break-even quando il profitto supera una soglia |
| `price_alert` | Notifica quando il prezzo supera/scende sotto un livello |
| `close_on_profit` | Chiude posizione al raggiungimento di un profitto target (€) |
| `close_on_loss` | Chiude posizione se la perdita supera un limite (€) |
| `close_on_time` | Chiude posizioni dopo un orario specificato (HH:MM) |
| `indicator_alert` | Alert basati su indicatori (RSI, MACD cross, Bollinger breakout) |
| `max_drawdown` | Chiude TUTTO se il drawdown dell'account supera una percentuale |

### Come Claude genera configurazioni monitor

Quando l'utente descrive regole di gestione automatica, Claude deve:

1. **Tradurre** le regole in formato JSON del monitor
2. **Suggerire `--dry-run`** per il primo test
3. **Includere sempre** la regola `max_drawdown` come protezione
4. **Spiegare** cosa farà ogni regola

Esempio:
- Utente: "Voglio che le mie posizioni vengano protette automaticamente:
  trailing stop a 20 pips, break-even dopo 15 pips di profitto,
  e chiudi tutto se perdo più del 3%"
- Claude genera un JSON config con 3 regole e la salva come file

### Struttura config monitor

```json
{
  "interval_seconds": 30,
  "log_file": "mt5_monitor_log.json",
  "rules": [
    {
      "name": "Nome descrittivo",
      "type": "trailing_stop",
      "enabled": true,
      "trail_points": 200,
      "symbol": "EURUSD"
    }
  ]
}
```

Per la documentazione completa delle regole, consultare: `references/monitor_rules.md`

### Alert con azioni automatiche

Le regole `price_alert` e `indicator_alert` possono includere un'azione da eseguire
automaticamente quando l'alert scatta:

```json
{
  "type": "price_alert",
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

## Flusso decisionale completo per Claude

Quando l'utente chiede un trade o una strategia, Claude segue questo flusso:

1. **Analisi** → `python mt5_indicators.py SYMBOL --analysis`
2. **Account** → `python mt5_trading.py account` (per saldo e margine)
3. **Calcolo lotto** → `python mt5_trading.py lot_size SYMBOL RISK SL_POINTS`
4. **Riepilogo** → Presenta all'utente: indicatori, direzione, volume, SL, TP, rischio
5. **Conferma** → Attendi OK dall'utente
6. **Esecuzione** → Genera il comando/strategia
7. **Monitoraggio** → Proponi config monitor se servono regole automatiche

## Note importanti

- Gli output sono **sempre in JSON** per parsing facile
- Il **magic number** identifica la strategia (utile per gestire più strategie)
- Claude deve suggerire magic numbers diversi per strategie diverse
- Se l'utente chiede dati OHLC o tick, Claude li analizza per supportare decisioni
- Il monitor scrive un log in `mt5_monitor_log.json` consultabile in qualsiasi momento
- Premere `Ctrl+C` per fermare il monitor in modo pulito
