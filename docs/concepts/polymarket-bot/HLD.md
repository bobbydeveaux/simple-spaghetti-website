# High-Level Design: f4aae091-e557-4fad-93ef-0c81a2a395e1

**Created:** 2026-02-16T15:21:50Z
**Status:** Draft

## 1. Architecture Overview

The Polymarket Bot follows a **single-process monolithic architecture** optimized for low-latency execution within tight 5-minute trading windows. The system operates as a stateful Python application with distinct layers for market connectivity, prediction logic, trade execution, and risk management.

**Architecture Pattern:** Event-driven loop with synchronous execution and asynchronous I/O for API calls and logging.

**Key Design Principles:**
- **Single-threaded execution loop** for deterministic behavior and simplified state management
- **Fail-fast design** with circuit breakers for API failures and emergency stops for risk violations
- **State persistence** after each trade settlement to enable crash recovery
- **Time-based orchestration** using 5-minute interval scheduling with sub-second precision

**Execution Flow:**
```
Initialization → API Authentication → 18-Interval Loop [
  Price Data Fetch (30s intervals) →
  Prediction Engine (RSI/EMA calculation) →
  Risk Check (volatility, drawdown) →
  Trade Submission →
  Position Monitoring (15s polls) →
  Settlement Detection →
  State Update (equity, streak, logs)
] → Shutdown
```

---

## 2. System Components

**2.1 MarketConnector**
- Handles Polymarket API authentication (API key or wallet-based)
- Fetches BTC 5-minute market metadata and current UP/DOWN odds
- Submits market orders with retry logic (max 3 attempts, exponential backoff)
- Polls settlement status every 15 seconds until outcome resolved

**2.2 PriceDataProvider**
- Connects to external BTC price feed (Binance WebSocket preferred, fallback to Coinbase/CoinGecko REST)
- Maintains rolling 30-minute price buffer (60 data points at 30s intervals)
- Validates price data integrity (anomaly detection for >10% single-tick moves)
- Calculates real-time volatility (standard deviation of last 10 prices)

**2.3 PredictionEngine**
- Computes 14-period RSI from rolling price buffer using Wilder's smoothing
- Calculates 9-period and 21-period EMA for crossover detection
- Applies deterministic signal rules:
  - UP: RSI < 30 OR (9-EMA > 21-EMA AND previous was 9-EMA ≤ 21-EMA)
  - DOWN: RSI > 70 OR (9-EMA < 21-EMA AND previous was 9-EMA ≥ 21-EMA)
  - Default: DOWN (conservative bias when no signal)
- Outputs prediction with confidence metadata (signal strength)

**2.4 CapitalAllocator**
- Tracks current equity, win streak, position history
- Calculates position size: `min(base_size * (1.5 ^ win_streak), max_exposure)`
- Constants: base_size=$5, multiplier=1.5, max_exposure=$30
- Validates position size against available equity (prevents overdraft)

**2.5 RiskManager**
- Monitors drawdown: `(starting_capital - current_equity) / starting_capital`
- Triggers emergency halt if drawdown > 30%
- Implements volatility filter: skip interval if price std dev > 2x baseline
- Enforces single-position constraint (blocks new trades if position open)

**2.6 StateManager**
- Persists bot state to JSON after each settlement: `{equity, win_streak, trade_count, last_position}`
- Enables recovery from crashes by reloading state on restart
- Maintains equity curve as time-series array
- Exports final equity curve to CSV on shutdown

**2.7 Logger**
- Asynchronous JSON logging for predictions and trade outcomes
- Prediction logs: `{timestamp, btc_price, rsi, ema9, ema21, signal, prediction}`
- Trade logs: `{settlement_time, prediction, actual_direction, win, pnl, position_size, equity, win_streak}`
- Flushes logs to disk every 5 intervals or on emergency stop

**2.8 Orchestrator**
- Main execution loop coordinating all components
- Interval scheduler using `time.sleep()` with drift correction
- Watchdog timer (2-minute inactivity threshold) with auto-restart signal
- Graceful shutdown handler (SIGINT/SIGTERM) for final log flush

---

## 3. Data Model

**3.1 BotState (Persistent)**
```json
{
  "starting_capital": 100.0,
  "current_equity": 105.5,
  "win_streak": 2,
  "trade_count": 5,
  "last_position": {
    "direction": "UP",
    "size": 11.25,
    "entry_time": "2026-02-16T15:30:00Z",
    "settlement_time": "2026-02-16T15:35:00Z",
    "outcome": "win",
    "pnl": 4.5
  },
  "equity_curve": [
    {"timestamp": "2026-02-16T15:05:00Z", "equity": 100.0},
    {"timestamp": "2026-02-16T15:10:00Z", "equity": 103.0}
  ],
  "baseline_volatility": 0.0015,
  "emergency_stop": false
}
```

**3.2 PriceDataBuffer (In-Memory)**
```python
prices: Deque[PricePoint]  # maxlen=60 (30 minutes of 30s data)
PricePoint = {
  "timestamp": datetime,
  "price": float,
  "source": str  # "binance"|"coinbase"|"coingecko"
}
```

**3.3 Position (In-Memory)**
```python
{
  "direction": "UP" | "DOWN",
  "size": float,
  "entry_time": datetime,
  "expected_settlement": datetime,  # entry_time + 5 minutes
  "market_id": str,
  "order_id": str,
  "status": "open" | "settled",
  "outcome": None | "win" | "loss",
  "pnl": None | float
}
```

**3.4 Prediction (Logged)**
```json
{
  "timestamp": "2026-02-16T15:04:30Z",
  "btc_price": 51234.56,
  "rsi_14": 28.5,
  "ema_9": 51230.12,
  "ema_21": 51245.78,
  "signal_type": "RSI_OVERSOLD",
  "prediction": "UP",
  "confidence": "high"
}
```

**3.5 TradeOutcome (Logged)**
```json
{
  "settlement_time": "2026-02-16T15:10:00Z",
  "prediction": "UP",
  "actual_direction": "UP",
  "win": true,
  "pnl": 4.50,
  "position_size": 11.25,
  "equity_before": 101.0,
  "equity_after": 105.5,
  "win_streak": 2,
  "market_odds": {"UP": 0.52, "DOWN": 0.48}
}
```

---

## 4. API Contracts

**4.1 Polymarket API**

**GET /markets/{market_id}**
- Request: `Authorization: Bearer {api_key}`
- Response:
```json
{
  "market_id": "btc-5min-20260216-1530",
  "question": "Will BTC be UP in next 5 minutes?",
  "outcomes": ["UP", "DOWN"],
  "odds": {"UP": 0.51, "DOWN": 0.49},
  "settlement_time": "2026-02-16T15:30:00Z",
  "status": "open"
}
```

**POST /orders**
- Request:
```json
{
  "market_id": "btc-5min-20260216-1530",
  "outcome": "UP",
  "amount": 11.25,
  "type": "market"
}
```
- Response:
```json
{
  "order_id": "ord_abc123",
  "status": "filled",
  "filled_amount": 11.25,
  "avg_price": 0.51
}
```

**GET /markets/{market_id}/resolution**
- Response:
```json
{
  "market_id": "btc-5min-20260216-1530",
  "resolved": true,
  "winning_outcome": "UP",
  "resolution_time": "2026-02-16T15:30:05Z"
}
```

**4.2 Binance WebSocket (Price Feed)**

**Stream:** `wss://stream.binance.com:9443/ws/btcusdt@ticker`
- Message:
```json
{
  "e": "24hrTicker",
  "s": "BTCUSDT",
  "c": "51234.56",  // last price
  "E": 1708098000000  // event time
}
```

**4.3 Fallback REST APIs**

**Coinbase:** `GET https://api.coinbase.com/v2/prices/BTC-USD/spot`
**CoinGecko:** `GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd`

---

## 5. Technology Stack

### Backend
- **Language:** Python 3.11
- **Core Libraries:**
  - `pandas` 2.0+ (price buffer management, indicator calculation)
  - `numpy` 1.24+ (numerical operations, statistics)
  - `pandas-ta` or `TA-Lib` (RSI, EMA computation)
  - `requests` 2.31+ (REST API calls with retry)
  - `websockets` 12.0+ (Binance price feed)
  - `asyncio` (async I/O for logging, concurrent API calls)
- **Wallet/Crypto:**
  - `web3.py` 6.0+ (if Polymarket requires on-chain tx signing)
  - `eth-account` (private key management for wallet-based auth)

### Frontend
- **N/A** (no UI; bot runs headless via CLI)

### Infrastructure
- **Deployment Target:** Single VPS or local machine (Ubuntu 22.04 LTS recommended)
- **Process Manager:** `systemd` service for auto-restart and logging
- **Time Sync:** `chrony` or `ntpd` for accurate interval timing
- **Environment:** `.env` file for secrets (API keys, private keys)

### Data Storage
- **State Persistence:** JSON file (`bot_state.json`) with atomic write-replace pattern
- **Logs:** Line-delimited JSON files (`predictions.jsonl`, `trades.jsonl`)
- **Equity Curve:** CSV export (`equity_curve.csv`) on shutdown
- **No Database Required:** All data fits in memory (<1MB for 18 trades)

---

## 6. Integration Points

**6.1 Polymarket API**
- **Protocol:** HTTPS REST + WebSocket for real-time market updates (if available)
- **Authentication:** API key (Bearer token) or wallet signature (EIP-712)
- **Rate Limits:** Assumed 60 req/min (well within bot's ~5 req/interval usage)
- **Error Handling:** Retry on 429/5xx, fail interval on auth errors (401/403)

**6.2 Binance WebSocket**
- **Primary Price Feed:** `wss://stream.binance.com:9443/ws/btcusdt@ticker`
- **Reconnection Logic:** Auto-reconnect on disconnect with 5s backoff
- **Data Validation:** Reject prices >10% deviation from last known price

**6.3 Coinbase REST API (Fallback)**
- **Endpoint:** `https://api.coinbase.com/v2/prices/BTC-USD/spot`
- **Polling Interval:** 30 seconds (only if Binance WebSocket unavailable)
- **Rate Limit:** 10 req/sec (far exceeds bot needs)

**6.4 CoinGecko API (Secondary Fallback)**
- **Endpoint:** `https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd`
- **Free Tier:** 50 calls/min (sufficient for 2 calls/min usage)
- **Used Only:** When both Binance and Coinbase fail

**6.5 System Clock (NTP)**
- **Requirement:** Time drift <500ms to ensure accurate 5-minute intervals
- **Validation:** Check NTP sync status on startup, fail if drift >1s

---

## 7. Security Architecture

**7.1 Credential Management**
- **Storage:** Environment variables loaded from `.env` file (never committed to git)
- **Variables:** `POLYMARKET_API_KEY`, `WALLET_PRIVATE_KEY` (if wallet-based auth)
- **File Permissions:** `.env` restricted to `chmod 600` (owner read/write only)
- **Alternative:** HashiCorp Vault or AWS Secrets Manager for production deployments

**7.2 API Security**
- **Transport:** All API calls over TLS 1.2+ with certificate validation
- **Request Signing:** Wallet-based auth uses EIP-712 signed messages with nonce/timestamp
- **Input Validation:** Sanitize all external data (price feeds, market odds) against schema
- **Rate Limiting:** Client-side throttling to stay under API limits

**7.3 Financial Controls**
- **Position Validation:** Assert `0 < position_size <= max_exposure` before order submission
- **Equity Validation:** Reject trades if `position_size > current_equity`
- **Overflow Protection:** Use `Decimal` type for currency calculations (avoid float precision errors)
- **Drawdown Enforcement:** Hard stop at 30% drawdown, no override mechanism

**7.4 Data Integrity**
- **State File:** Atomic write-replace using temp file + `os.rename()` (prevents corruption on crash)
- **Log Integrity:** Append-only JSONL files with line-level error recovery
- **Price Anomaly Detection:** Flag and skip intervals if price moves >10% in 30s (likely data error)

**7.5 Operational Security**
- **No Remote Access:** Bot runs locally or on isolated VPS (no external SSH/RDP during trading)
- **Process Isolation:** Run as non-root user with minimal file system permissions
- **Secrets Cleanup:** Clear sensitive env vars from memory after loading

---

## 8. Deployment Architecture

**8.1 Single-Instance Deployment**
- **Target:** Ubuntu 22.04 LTS VPS (1 vCPU, 1GB RAM sufficient)
- **Containerization:** Optional Docker container for reproducibility
  - Base image: `python:3.11-slim`
  - Dependencies: `requirements.txt` (pinned versions)
  - Volume mount: `/app/data` for state/logs persistence

**8.2 systemd Service (Non-Containerized)**
```ini
[Unit]
Description=Polymarket Trading Bot
After=network-online.target

[Service]
Type=simple
User=polybot
WorkingDirectory=/opt/polymarket-bot
ExecStart=/opt/polymarket-bot/venv/bin/python main.py
Restart=on-failure
RestartSec=30
EnvironmentFile=/opt/polymarket-bot/.env

[Install]
WantedBy=multi-user.target
```

**8.3 Docker Deployment (Optional)**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```
- Run: `docker run -v ./data:/app/data --env-file .env polymarket-bot`

**8.4 State Persistence**
- **Local:** `./data/bot_state.json`, `./data/predictions.jsonl`, `./data/trades.jsonl`
- **Backup:** Optional post-run upload to S3/GCS for audit trail (out of scope for MVP)

**8.5 Time Synchronization**
- **Pre-Deployment:** Verify NTP sync: `timedatectl status`
- **Monitoring:** Bot checks time drift on startup, logs warning if >500ms

---

## 9. Scalability Strategy

**9.1 Current Scope (Not Scaled)**
- **Single Bot Instance:** Designed for one concurrent trading session (90 minutes)
- **No Horizontal Scaling:** Stateful design prevents multi-instance deployment without coordination
- **Resource Footprint:** <50MB RAM, <1% CPU (mostly idle waiting for intervals)

**9.2 Future Scalability Considerations**
- **Multi-Market Support:** Extend to multiple BTC intervals or other assets by running isolated bot instances
  - Each instance manages independent state file
  - Shared capital pool requires external coordinator (out of scope)
- **Vertical Scaling:** Current architecture supports up to ~100 concurrent markets on single 4-core instance
- **Data Scaling:** 18 trades × ~500 bytes/trade = 9KB logs (no storage concerns)

**9.3 Performance Optimization**
- **Async I/O:** API calls and logging use `asyncio` to prevent blocking execution loop
- **Price Buffer:** Fixed-size deque (60 elements) for O(1) append/pop operations
- **Indicator Caching:** Recompute RSI/EMA only on new price data (not every poll)

---

## 10. Monitoring & Observability

**10.1 Logging Strategy**
- **Structured Logs:** Line-delimited JSON for easy parsing
  - `predictions.jsonl`: All prediction signals with technical indicator values
  - `trades.jsonl`: All trade outcomes with P&L and equity updates
  - `bot.log`: Application-level events (startup, errors, shutdown)
- **Log Levels:**
  - INFO: Predictions, trades, state updates
  - WARNING: Volatility filter triggered, API retries
  - ERROR: API failures, validation errors
  - CRITICAL: Emergency stop, unrecoverable errors

**10.2 Metrics Tracked**
- **Trade Metrics:** Win rate, average P&L, max win streak, max drawdown
- **Execution Metrics:** API latency (p50/p95), prediction compute time, order fill time
- **System Metrics:** Watchdog triggers, price feed disconnects, state save failures

**10.3 Real-Time Monitoring (Optional)**
- **Console Output:** Live stream of key events (predictions, trade outcomes) to stdout
- **File Watching:** `tail -f trades.jsonl | jq .` for real-time log viewing
- **Equity Tracking:** Print equity after each settlement for manual monitoring

**10.4 Alerting (Out of Scope for MVP)**
- **Future Enhancement:** Email/SMS alerts on emergency stop or critical errors
- **Monitoring Tools:** Prometheus + Grafana for production deployments (not in initial scope)

**10.5 Post-Run Analysis**
- **Equity Curve CSV:** Import into Excel/Python for visualization
- **Log Aggregation:** Parse JSONL files to compute win rate, Sharpe ratio, etc.
- **Performance Replay:** Reconstruct full trading session from logs for debugging

---

## 11. Architectural Decisions (ADRs)

**ADR-001: Monolithic Single-Process Architecture**
- **Decision:** Implement as single Python process with synchronous execution loop
- **Rationale:**
  - Simplifies state management (no distributed consensus required)
  - Minimizes latency (no inter-process communication overhead)
  - Sufficient for 18-trade horizon (no scaling needs)
  - Easier to debug and reason about deterministic behavior
- **Trade-offs:** Cannot scale horizontally without refactor
- **Alternatives Considered:** Microservices (rejected: over-engineered), multi-threading (rejected: adds complexity)

**ADR-002: Binance WebSocket for Primary Price Feed**
- **Decision:** Use Binance WebSocket API for real-time BTC prices, fallback to Coinbase/CoinGecko REST
- **Rationale:**
  - Lowest latency (<50ms vs 200-500ms for REST)
  - No rate limits on public WebSocket streams
  - Binance has highest BTC/USDT liquidity (most accurate pricing)
- **Trade-offs:** Requires WebSocket reconnection logic
- **Alternatives Considered:** Coinbase WebSocket (rejected: more complex auth), CoinGecko only (rejected: rate limits)

**ADR-003: JSON File Storage for State Persistence**
- **Decision:** Store bot state in local JSON file with atomic write-replace
- **Rationale:**
  - State size <1KB (fits in single file)
  - No database overhead (setup, maintenance, failure modes)
  - Atomic rename ensures crash-safe writes
  - Easy manual inspection and debugging
- **Trade-offs:** Not suitable for multi-instance deployments
- **Alternatives Considered:** SQLite (rejected: overkill), Redis (rejected: external dependency)

**ADR-004: Win-Streak Capital Allocation (Not Martingale)**
- **Decision:** Scale position size by 1.5x per consecutive win, reset to base on loss
- **Rationale:**
  - Exploits winning streaks without exponential risk of martingale
  - Bounded by max_exposure cap to prevent account wipeout
  - Allows capital growth while limiting downside
- **Trade-offs:** Lower upside than aggressive strategies
- **Alternatives Considered:** Fixed size (rejected: no compounding), martingale (rejected: catastrophic risk)

**ADR-005: 30% Max Drawdown Emergency Stop**
- **Decision:** Hard stop all trading if equity drops 30% below starting capital
- **Rationale:**
  - Prevents total account loss from extended losing streaks
  - 30% threshold allows strategy to recover from variance while limiting tail risk
  - Preserves 70% of capital for manual intervention or strategy revision
- **Trade-offs:** May stop prematurely during recoverable drawdowns
- **Alternatives Considered:** No stop (rejected: catastrophic risk), 50% stop (rejected: too permissive)

**ADR-006: RSI + EMA Crossover Prediction Logic**
- **Decision:** Use 14-period RSI and 9/21 EMA crossover as deterministic signals
- **Rationale:**
  - Well-established technical indicators with clear signal rules
  - RSI identifies overbought/oversold (mean reversion)
  - EMA crossover captures momentum shifts
  - Computationally cheap (<100ms for 60-point buffer)
- **Trade-offs:** No guarantee of profitability (market randomness)
- **Alternatives Considered:** Machine learning (rejected: not deterministic), order book analysis (rejected: data unavailable)

**ADR-007: Volatility Filter for Interval Skipping**
- **Decision:** Skip trading intervals if price std dev exceeds 2x baseline volatility
- **Rationale:**
  - High volatility increases prediction error and slippage
  - Protects against flash crashes or anomalous price spikes
  - Baseline volatility computed from first 10 prices (adaptive threshold)
- **Trade-offs:** May miss profitable opportunities in volatile markets
- **Alternatives Considered:** No filter (rejected: excessive risk), fixed threshold (rejected: not adaptive)

**ADR-008: Async Logging to Prevent Execution Blocking**
- **Decision:** Use `asyncio` for log writes and non-critical I/O operations
- **Rationale:**
  - Prevents log I/O from delaying trade execution (5-minute window is tight)
  - Allows parallel API calls for price feed + market data fetching
  - Maintains deterministic execution order in main loop
- **Trade-offs:** Slightly more complex error handling for async tasks
- **Alternatives Considered:** Synchronous logging (rejected: blocks execution), separate log process (rejected: over-engineered)

**ADR-009: Exponential Backoff Retry for API Failures**
- **Decision:** Retry failed API calls up to 3 times with exponential backoff (1s, 2s, 4s)
- **Rationale:**
  - Handles transient network errors and API rate limits
  - Bounded retry attempts prevent infinite loops
  - Exponential backoff reduces server load
- **Trade-offs:** May exceed 5-minute window if all retries exhaust
- **Alternatives Considered:** No retries (rejected: too fragile), unlimited retries (rejected: risk of infinite hang)

**ADR-010: Default to DOWN Prediction on No Signal**
- **Decision:** When neither RSI nor EMA crossover triggers, predict DOWN
- **Rationale:**
  - Conservative bias reduces risk in uncertain conditions
  - BTC historically exhibits slight downward bias in short intervals (mean reversion)
  - Ensures bot always generates a prediction (no abstentions)
- **Trade-offs:** May underperform in strong uptrends
- **Alternatives Considered:** Skip interval (rejected: reduces trade count), random (rejected: not deterministic)

---

## Appendix: PRD Reference

# Product Requirements Document: Polymarket Bot

Design a fully defined automated trading bot for Polymarket with the following requirements:
Capital: $100
Market: BTC 5-minute directional market (UP/DOWN contracts)
Time Horizon: 90 minutes (18 consecutive 5-minute intervals)
The bot must:
Connect to Polymarket API
Fetch current BTC directional market odds
Track 5-minute settlement times
Submit trades programmatically
Prediction Engine
Define deterministic logic for predicting UP or DOWN
Specify required data inputs (price feed, indicators, order book, etc.)
Ensure the logic is consistent and rule-based
Execution Logic
Enter one position per 5-minute interval
Avoid overlapping trades
Track open/closed positions
Capital Allocation Strategy
Implement a win-streak-based scaling strategy (not loss-doubling martingale unless explicitly justified)
Define:
Base position size
Scaling multiplier
Maximum exposure cap
Stop-loss rules
Max drawdown threshold
Risk Controls
Prevent account wipeout
Define failure conditions
Include volatility safeguards
Logging & State
Log predictions
Log trade outcomes
Maintain equity curve
Reset logic after streak break
Output:
Architecture overview
Strategy logic
Pseudocode or flow diagram
Risk analysis of the strategy
Do not assume perfect foresight. Assume realistic market behavior.

**Created:** 2026-02-16T15:20:30Z
**Status:** Draft

## 1. Overview

**Concept:** Polymarket Bot

Design a fully defined automated trading bot for Polymarket with the following requirements:
Capital: $100
Market: BTC 5-minute directional market (UP/DOWN contracts)
Time Horizon: 90 minutes (18 consecutive 5-minute intervals)
The bot must:
Connect to Polymarket API
Fetch current BTC directional market odds
Track 5-minute settlement times
Submit trades programmatically
Prediction Engine
Define deterministic logic for predicting UP or DOWN
Specify required data inputs (price feed, indicators, order book, etc.)
Ensure the logic is consistent and rule-based
Execution Logic
Enter one position per 5-minute interval
Avoid overlapping trades
Track open/closed positions
Capital Allocation Strategy
Implement a win-streak-based scaling strategy (not loss-doubling martingale unless explicitly justified)
Define:
Base position size
Scaling multiplier
Maximum exposure cap
Stop-loss rules
Max drawdown threshold
Risk Controls
Prevent account wipeout
Define failure conditions
Include volatility safeguards
Logging & State
Log predictions
Log trade outcomes
Maintain equity curve
Reset logic after streak break
Output:
Architecture overview
Strategy logic
Pseudocode or flow diagram
Risk analysis of the strategy
Do not assume perfect foresight. Assume realistic market behavior.

**Description:** Polymarket Bot

Design a fully defined automated trading bot for Polymarket with the following requirements:
Capital: $100
Market: BTC 5-minute directional market (UP/DOWN contracts)
Time Horizon: 90 minutes (18 consecutive 5-minute intervals)
The bot must:
Connect to Polymarket API
Fetch current BTC directional market odds
Track 5-minute settlement times
Submit trades programmatically
Prediction Engine
Define deterministic logic for predicting UP or DOWN
Specify required data inputs (price feed, indicators, order book, etc.)
Ensure the logic is consistent and rule-based
Execution Logic
Enter one position per 5-minute interval
Avoid overlapping trades
Track open/closed positions
Capital Allocation Strategy
Implement a win-streak-based scaling strategy (not loss-doubling martingale unless explicitly justified)
Define:
Base position size
Scaling multiplier
Maximum exposure cap
Stop-loss rules
Max drawdown threshold
Risk Controls
Prevent account wipeout
Define failure conditions
Include volatility safeguards
Logging & State
Log predictions
Log trade outcomes
Maintain equity curve
Reset logic after streak break
Output:
Architecture overview
Strategy logic
Pseudocode or flow diagram
Risk analysis of the strategy
Do not assume perfect foresight. Assume realistic market behavior.

---

## 2. Goals

- Execute automated trading on Polymarket BTC 5-minute directional markets across 18 consecutive intervals within 90 minutes
- Implement deterministic prediction logic using technical indicators (RSI, EMA crossover, momentum) with real-time BTC price data
- Apply win-streak-based capital allocation starting at $5 base size, scaling by 1.5x per win, capped at $30 max exposure
- Maintain capital preservation with 30% max drawdown threshold and emergency stop-loss to prevent account wipeout
- Generate comprehensive trading logs tracking predictions, outcomes, equity curve, and win/loss streaks for performance analysis

---

## 3. Non-Goals

- Portfolio diversification across multiple markets or cryptocurrencies beyond BTC 5-minute directional contracts
- Machine learning or adaptive prediction models that learn from historical performance
- Real-time market making, liquidity provision, or arbitrage strategies
- Integration with external portfolio management or tax reporting tools
- Multi-account management or social trading features

---

## 4. User Stories

- As a trader, I want the bot to automatically connect to Polymarket API so that I can trade BTC directional markets without manual intervention
- As a trader, I want the bot to fetch current market odds and BTC price data every 5 minutes so that predictions are based on recent information
- As a trader, I want the bot to use RSI and EMA crossover indicators to predict UP/DOWN so that trading decisions follow consistent technical analysis
- As a trader, I want position sizing to scale by 1.5x after wins so that I can compound gains during favorable streaks
- As a trader, I want position sizing to reset to base after losses so that losing streaks don't exponentially drain capital
- As a trader, I want the bot to enforce a $30 maximum position size so that no single trade risks excessive capital
- As a trader, I want the bot to halt trading if drawdown exceeds 30% so that my account is protected from catastrophic loss
- As a trader, I want each trade outcome logged with timestamp, prediction, actual result, and P&L so that I can analyze performance
- As a trader, I want to see an equity curve updated after each settlement so that I can monitor portfolio growth
- As a trader, I want the bot to prevent overlapping trades so that capital allocation remains controlled and predictable

---

## 5. Acceptance Criteria

**AC-001: Market Connection**
- Given the bot starts, when it initializes, then it successfully authenticates with Polymarket API and retrieves BTC 5-minute market metadata

**AC-002: Prediction Engine**
- Given BTC price data is available, when the prediction logic runs, then it outputs UP or DOWN based on RSI < 30 (UP), RSI > 70 (DOWN), or EMA crossover signals

**AC-003: Trade Execution**
- Given a prediction is generated, when the bot submits a trade, then the order is placed on Polymarket with correct direction and position size before the 5-minute interval expires

**AC-004: Capital Allocation**
- Given a win streak of 2 trades, when calculating next position size, then size = base_size * (1.5 ^ streak) capped at $30
- Given a loss occurs, when updating position size, then size resets to $5 base

**AC-005: Risk Controls**
- Given current equity drops 30% below starting capital, when drawdown check runs, then the bot halts all trading and logs emergency stop

**AC-006: Logging**
- Given a trade settles, when outcome is determined, then a log entry is created with timestamp, prediction, actual direction, P&L, position size, and current equity

---

## 6. Functional Requirements

**FR-001:** Connect to Polymarket API using authenticated REST/WebSocket endpoints for market data and order submission
**FR-002:** Fetch BTC spot price from external data provider (Binance, Coinbase, or CoinGecko API) every 30 seconds
**FR-003:** Calculate 14-period RSI and 9/21 EMA crossover using rolling price windows updated each fetch cycle
**FR-004:** Generate UP prediction if RSI < 30 or 9-EMA crosses above 21-EMA; DOWN if RSI > 70 or 9-EMA crosses below 21-EMA
**FR-005:** Default to DOWN if no signal triggers (conservative bias)
**FR-006:** Query Polymarket for current UP/DOWN contract odds before each trade to estimate expected payout
**FR-007:** Submit market order for predicted direction with position size determined by capital allocation logic
**FR-008:** Track open position with entry time, direction, size, and expected settlement timestamp
**FR-009:** Poll market settlement status every 15 seconds; mark position closed when outcome is resolved
**FR-010:** Update win streak counter: increment on win, reset to 0 on loss
**FR-011:** Calculate next position size as base_size * (multiplier ^ win_streak), capped at max_exposure
**FR-012:** Calculate current equity as starting_capital + sum(all_trade_pnl)
**FR-013:** Check if (starting_capital - current_equity) / starting_capital > max_drawdown_threshold; if true, trigger emergency halt
**FR-014:** Check if price volatility (std dev of last 10 prices) exceeds 2x normal range; if true, skip the current interval
**FR-015:** Log each prediction with timestamp, BTC price, RSI, EMA values, signal type, and predicted direction to JSON file
**FR-016:** Log each trade outcome with settlement time, actual direction, win/loss, P&L, position size, new equity, win streak to JSON file
**FR-017:** Maintain equity curve as array of (timestamp, equity) tuples; export to CSV on completion
**FR-018:** Implement graceful shutdown on completion of 18 intervals or emergency stop, flushing all logs and final state

---

## 7. Non-Functional Requirements

### Performance
- API response time for market data fetch must be under 500ms to allow prediction and order submission within each 5-minute window
- Prediction engine must calculate indicators and generate signal in under 100ms
- Order submission latency must be under 1 second to ensure execution before interval close
- Log writes must be asynchronous to avoid blocking trade execution loop

### Security
- API credentials stored in environment variables or secure vault, never hardcoded
- All API communication over HTTPS/WSS with certificate validation
- Position size and capital calculations validated to prevent integer overflow or negative values
- Input validation on all external data (price feeds, market odds) to detect anomalies or manipulation attempts

### Scalability
- System designed for single-bot operation on $100 capital; not required to scale to multiple concurrent bots
- Stateful design allows process restart with state recovery from last logged equity and streak values
- Architecture modular enough to extend to additional markets without core logic refactor

### Reliability
- Implement exponential backoff retry logic for API failures (max 3 retries per call)
- Graceful degradation: if price feed unavailable, skip interval rather than trade on stale data
- State persistence after each trade outcome to enable recovery from crashes
- Watchdog timer to detect execution loop hangs; auto-restart if no activity for 2 minutes

---

## 8. Dependencies

- Polymarket API (REST/WebSocket) for market data retrieval and order execution
- External BTC price feed API (Binance, Coinbase, or CoinGecko) for real-time spot price
- Technical analysis library (TA-Lib, pandas-ta, or custom implementation) for RSI and EMA calculation
- Blockchain wallet integration (if Polymarket requires on-chain settlement) for transaction signing
- Python runtime (3.9+) with dependencies: requests, websockets, pandas, numpy
- JSON file storage for logs and state persistence
- System clock synchronization (NTP) to ensure accurate 5-minute interval timing

---

## 9. Out of Scope

- Backtesting framework or historical simulation beyond the live 90-minute window
- User interface, dashboard, or real-time visualization of trades
- Integration with other trading platforms or cross-exchange arbitrage
- Tax reporting, trade export to accounting software, or compliance features
- Multi-user support, authentication, or role-based access control
- Mobile app or notification system for trade alerts
- Advanced order types (limit orders, stop-loss orders, trailing stops) beyond market execution
- Market making, liquidity provision, or yield farming strategies
- Predictive model training, hyperparameter optimization, or A/B testing of strategies

---

## 10. Success Metrics

- 100% uptime across all 18 trading intervals without crashes or missed trades
- Prediction engine executes and generates signal for all 18 intervals within 5-minute window
- Zero trades rejected due to insufficient capital, invalid order parameters, or API errors
- Emergency stop triggers correctly if drawdown exceeds 30%, preventing further losses
- All 18 trade outcomes logged with complete data (timestamp, prediction, outcome, P&L, equity)
- Final equity curve exported to CSV with 18 data points corresponding to each settlement
- Win-streak scaling correctly applies multiplier and caps at $30 max exposure as per capital allocation rules
- Volatility safeguard correctly skips intervals when price std dev exceeds 2x threshold (if triggered)

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers