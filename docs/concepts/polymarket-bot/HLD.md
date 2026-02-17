# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-16T16:06:43Z
**Status:** Draft

## 1. Architecture Overview

Single-process monolithic application with event-driven loop architecture. The bot runs as a standalone Python process orchestrating four primary modules: Market Data Ingestion, Prediction Engine, Trade Execution, and Risk Manager. Main control loop iterates every 5 minutes for 90 minutes (18 cycles), triggering sequential pipeline: data fetch → prediction → risk check → trade execution → logging. State persists to local JSON files after each cycle for crash recovery.

---

## 2. System Components

**Main Orchestrator**: Event loop managing 5-minute interval timing, component coordination, and graceful shutdown on drawdown breach or completion.

**Market Data Service**: Fetches BTC price data from Binance WebSocket, calculates technical indicators (RSI, MACD), retrieves Polymarket odds via REST API.

**Prediction Engine**: Deterministic rule-based signal generator using configurable technical indicators. Inputs: RSI (configurable period, default 14), MACD (configurable fast/slow/signal periods, defaults 12/26/9), order book imbalance. Outputs: UP/DOWN/SKIP decision with confidence score and reasoning. Configuration via environment variables allows tuning thresholds (RSI oversold/overbought, order book bullish/bearish) without code changes.

**Position Manager**: Tracks current position state (entry time, size, direction), prevents overlapping trades, records settlements.

**Capital Allocator**: Calculates position size using win-streak multiplier (base=$5, multiplier=1.5x, cap=$25), maintains streak counter.

**Risk Controller**: Pre-trade checks for max drawdown (30%), volatility circuit breaker (3% 5-min range), halts trading on breach.

**State Persistence**: JSON-based logging for trades, equity curve, and bot state. Writes after each cycle.

---

## 3. Data Model

**BotState** (persisted JSON):
- current_capital: float
- starting_capital: float (constant $100)
- win_streak: int
- total_trades: int
- is_active: bool

**Trade** (log entry):
- timestamp: ISO8601
- interval_number: int (1-18)
- prediction: "UP" | "DOWN" | "SKIP"
- odds: float
- position_size: float
- outcome: "WIN" | "LOSS" | "PENDING"
- pnl: float
- capital_after: float

**Position** (in-memory):
- direction: "UP" | "DOWN"
- entry_time: timestamp
- settlement_time: timestamp
- size: float
- status: "OPEN" | "SETTLED"

**MarketData** (in-memory):
- btc_price: float
- rsi: float (calculated with configurable period)
- macd_line: float (calculated with configurable fast/slow periods)
- macd_signal: float (calculated with configurable signal period)
- order_book_imbalance: float
- polymarket_odds_up: float
- polymarket_odds_down: float

**PredictionSignal** (in-memory):
- signal: SignalType (UP/DOWN/SKIP)
- confidence: Decimal (0-1 range)
- rsi: Decimal
- macd_line: Decimal
- macd_signal: Decimal
- order_book_imbalance: Decimal
- btc_price: Optional[Decimal]
- timestamp: datetime
- reasoning: str (human-readable explanation)

---

## 4. API Contracts

**Binance WebSocket** (external):
- Stream: `wss://stream.binance.com:9443/ws/btcusdt@kline_1m`
- Response: `{s: "BTCUSDT", k: {c: "43250.00", h: "43300", l: "43200"}}`

**Polymarket REST API** (external):
- GET `/markets?asset=BTC&interval=5m`
- Response: `{market_id: "abc123", odds_yes: 0.52, odds_no: 0.48, settlement_time: "..."}`
- POST `/orders` Body: `{market_id, side: "YES"|"NO", amount, type: "MARKET"}`
- Response: `{order_id, status, filled_amount}`

**Internal Data Flow**:
- MarketDataService → PredictionEngine: MarketData object
- PredictionEngine → RiskController: {signal: "UP"|"DOWN", confidence: float}
- RiskController → CapitalAllocator: approved: bool
- CapitalAllocator → TradeExecutor: {direction, size}

---

## 5. Technology Stack

### Backend
- **Python 3.10+**: Core runtime
- **pandas**: Time series calculations for indicators
- **ta-lib**: Technical analysis (RSI, MACD)
- **websocket-client**: Binance real-time price feed
- **requests**: HTTP client for Polymarket API
- **python-dotenv**: Environment variable management

### Frontend
N/A (headless bot)

### Infrastructure
- **Docker** (optional): Container for isolated execution environment
- **systemd** (Linux): Process supervisor for production runs
- **cron**: Scheduled execution trigger

### Data Storage
- **Local filesystem**: JSON files for state (`bot_state.json`, `trades.log`)
- **In-memory**: Python dictionaries/dataclasses for active position tracking

---

## 6. Integration Points

**Binance WebSocket API**: Real-time BTC/USDT 1-minute candlestick data for indicator calculation. Fallback to REST API (`/api/v3/klines`) if WebSocket disconnects.

**Polymarket API**: Market discovery (5-minute BTC directional markets), odds retrieval, order placement, settlement polling. Authentication via API key in `Authorization: Bearer <token>` header.

**CoinGecko API** (fallback): If Binance unavailable, use `/simple/price?ids=bitcoin&vs_currencies=usd` for spot price (higher latency).

**Local State Files**: Read `bot_state.json` on startup for crash recovery. Append to `trades.log` after each interval.

---

## 7. Security Architecture

**API Key Management**: Store Polymarket API key and secret in `.env` file (never committed). Load via `os.getenv()` at runtime.

**Transport Security**: All external API calls over HTTPS/WSS. Certificate validation enabled.

**Input Validation**: Sanitize all external data (price feeds, API responses) with type checks and range validation before processing.

**Secrets Rotation**: Manual rotation process (not automated). Keys stored with 400 permissions on Linux.

**Error Handling**: Never log sensitive credentials. Redact API keys in error messages.

---

## 8. Deployment Architecture

**Development**: Run directly via `python main.py` with `.env` configuration. Logs to stdout and `trades.log`.

**Production**: Dockerized container with mounted volume for persistent state. Image: `python:3.10-slim` + dependencies.

**Container Orchestration**: Single-instance execution (no clustering needed). Docker Compose for local multi-component testing.

**Execution Model**: Scheduled via cron or triggered manually. Runs for exactly 90 minutes then exits.

---

## 9. Scalability Strategy

**Vertical Scaling Only**: Single-threaded execution sufficient for 18 trades. No horizontal scaling needed.

**Resource Limits**: Container capped at 512MB RAM, 0.5 CPU cores. Current load well below limits.

**Future Expansion**: Modular design allows adding new market types (10-minute intervals, ETH contracts) without core refactor. Multi-market support would require async execution model (asyncio).

---

## 10. Monitoring & Observability

**Logging**: Structured JSON logs to `trades.log` and stdout. Fields: timestamp, level, component, message, trade_data.

**Metrics**: Track per-cycle execution time, API latency, prediction generation time. Log to `metrics.log` every interval.

**Alerting**: Critical errors (API failure, max drawdown breach) trigger log entries with `CRITICAL` level. External monitoring scrapes logs for alerts.

**Health Checks**: Pre-flight validation on startup: API connectivity, sufficient capital, market availability.

**Post-Run Analysis**: Equity curve visualization from `trades.log` using matplotlib (offline script).

---

## 11. Architectural Decisions (ADRs)

**ADR-001 Monolith over Microservices**: Single-process design chosen for simplicity. 90-minute runtime with 18 transactions doesn't justify distributed architecture overhead.

**ADR-002 Synchronous Execution**: Sequential pipeline (data→predict→trade) avoids race conditions. Async not needed given 5-minute intervals provide ample time budget.

**ADR-003 JSON over Database**: File-based persistence sufficient for 18 records. Avoids database setup complexity. Acceptable for single-instance deployment.

**ADR-004 Binance Primary, CoinGecko Fallback**: Binance WebSocket provides lowest latency (<1s). CoinGecko as backup tolerates higher latency (3-5s) within performance budget.

**ADR-005 Deterministic Rules over ML**: Rule-based prediction (RSI+MACD thresholds) ensures reproducibility and auditability. ML excluded per PRD non-goals.

**ADR-006 Win-Streak Scaling**: Multiplier strategy (1.5^streak) balances growth on winning runs vs capital preservation. Max cap ($25) prevents over-concentration.

**ADR-007 Circuit Breaker on Volatility**: 3% 5-minute price range threshold protects against low-liquidity or flash-crash scenarios where prediction signals unreliable.

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

**Created:** 2026-02-16T16:05:51Z
**Status:** Draft

## 1. Overview

**Concept:** Polymarket Bot

**Description:** Automated trading bot that executes 18 consecutive 5-minute BTC directional trades on Polymarket using $100 capital, a deterministic prediction engine based on technical indicators, and a win-streak scaling strategy with comprehensive risk controls to prevent account wipeout.

---

## 2. Goals

- Execute 18 consecutive trades over 90 minutes on BTC 5-minute directional markets with zero overlap
- Implement deterministic prediction logic using BTC price feeds, RSI, MACD, and order book imbalance
- Scale position sizes dynamically based on win streaks while respecting maximum exposure caps
- Maintain complete audit trail of predictions, trades, outcomes, and equity curve
- Prevent total capital loss through max drawdown thresholds and volatility circuit breakers

---

## 3. Non-Goals

- Manual trading interface or user intervention during execution
- Support for markets other than BTC 5-minute directional contracts
- Machine learning or adaptive prediction models
- Backtesting infrastructure or historical performance simulation

---

## 4. User Stories

- As a trader, I want the bot to automatically connect to Polymarket API so that I can trade without manual intervention
- As a trader, I want deterministic UP/DOWN predictions based on technical indicators so that strategy behavior is consistent
- As a trader, I want position sizes to increase on win streaks so that I can capitalize on favorable market conditions
- As a trader, I want automatic position tracking so that I never have overlapping trades in the same interval
- As a trader, I want trading to halt at 30% drawdown so that I don't lose my entire capital
- As a trader, I want complete logs of all predictions and outcomes so that I can analyze performance
- As a trader, I want volatility checks before each trade so that the bot doesn't trade in unstable markets

---

## 5. Acceptance Criteria

**Given** the bot is initialized with $100 capital, **When** 90 minutes elapse, **Then** exactly 18 trades are executed with no overlaps
**Given** BTC price data is available, **When** prediction is requested, **Then** deterministic UP/DOWN signal is generated using RSI, MACD, and order book data
**Given** a win streak of 2, **When** next position is sized, **Then** position size = base_size * (1.5^2) capped at $25
**Given** current drawdown reaches 30%, **When** checked before trade, **Then** bot halts all trading and logs failure
**Given** a trade settles, **When** outcome is recorded, **Then** equity curve, streak counter, and trade log are updated

---

## 6. Functional Requirements

- FR-001: Connect to Polymarket API and authenticate using provided credentials
- FR-002: Fetch BTC 5-minute directional market odds and settlement times via API
- FR-003: Retrieve BTC price feed from external source (Binance/CoinGecko) with <5s latency
- FR-004: Calculate RSI (configurable period, default 14), MACD (configurable periods, defaults 12,26,9), and order book imbalance from data inputs
- FR-005: Generate UP prediction if RSI<oversold_threshold (default 30) AND MACD bullish crossover, DOWN if RSI>overbought_threshold (default 70) AND MACD bearish crossover (all thresholds configurable)
- FR-006: Submit market orders to Polymarket with calculated position size before interval closes
- FR-007: Track open position status and settlement outcome for each 5-minute interval
- FR-008: Implement base position $5, win-streak multiplier 1.5x, max exposure $25 per trade
- FR-009: Reset streak counter to 0 on any loss and recalculate position size
- FR-010: Enforce max drawdown threshold of 30% from starting capital ($70 floor)
- FR-011: Check BTC volatility (5-min price range >3%) and skip trade if exceeded
- FR-012: Log timestamp, prediction, odds, position size, outcome, PnL to JSON file per trade

---

## 7. Non-Functional Requirements

### Performance
- API response time <2s for market data retrieval
- Trade submission latency <3s from decision to order placement
- System uptime 99%+ during 90-minute trading window

### Security
- Store API keys in environment variables, never hardcoded
- Use HTTPS for all API communications
- Validate all external data inputs to prevent injection attacks

### Scalability
- Single-threaded execution sufficient for 18 trades over 90 minutes
- Modular architecture to allow future expansion to other markets

### Reliability
- Graceful degradation if price feed unavailable (skip interval, log error)
- Automatic retry logic (max 3 attempts) for failed API calls
- State persistence to disk after each trade to enable recovery

---

## 8. Dependencies

- Polymarket API (market data, order placement, settlement tracking)
- BTC price feed (Binance WebSocket API or CoinGecko REST API)
- Python libraries: requests, websocket-client, pandas, ta-lib
- Local file system for state persistence and logging

---

## 9. Out of Scope

- Graphical user interface or real-time dashboard
- Support for multiple concurrent markets or asset classes
- Historical backtesting framework or performance optimization
- Multi-account portfolio management
- Integration with external wallet management systems
- Automated capital replenishment or withdrawal

---

## 10. Success Metrics

- 100% trade execution rate (18/18 trades placed successfully)
- Zero overlapping positions across all intervals
- Max drawdown stays below 30% threshold
- Complete audit trail with 18 log entries matching trade count
- Prediction engine generates signal within 5s for each interval
- Bot survives full 90-minute window without critical failures

---

## Appendix: Clarification Q&A

### Clarification Questions & Answers