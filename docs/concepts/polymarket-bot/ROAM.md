# ROAM Analysis: polymarket-bot

**Feature Count:** 8
**Created:** 2026-02-16T16:17:43Z

## Risks

1. **Polymarket API Availability and Stability** (High): The entire system depends on undocumented/hypothetical Polymarket API endpoints. The LLD references `https://api.polymarket.com/v1` as "hypothetical, actual endpoint TBD". If the real API differs significantly in authentication, rate limits, market data structure, or settlement polling mechanisms, the bot may fail completely or require substantial rework. Additionally, API downtime during the 90-minute window would halt trading.

2. **Technical Indicator Signal Quality** (High): The deterministic prediction engine relies on rigid thresholds (RSI<30/RSI>70, MACD crossovers, order book imbalance) that may produce poor signals in ranging or low-volatility BTC markets. The 5-minute interval is extremely short for technical analysis, and the strategy has no backtesting validation. High likelihood of consistent losses leading to rapid drawdown.

3. **Win-Streak Capital Scaling Risk** (Medium): The 1.5x multiplier on win streaks can quickly escalate position sizes (streak of 3 = $16.87, streak of 4 = $25 cap). A single bad streak could wipe out gains from multiple wins. The $25 cap (25% of capital) combined with potential for consecutive losses creates significant drawdown risk despite the 30% circuit breaker.

4. **WebSocket Connection Stability** (Medium): Binance WebSocket disconnections during critical intervals could force fallback to CoinGecko API with higher latency (3-5s vs <1s). This latency could result in stale price data for indicator calculations, leading to incorrect predictions. The 100-price buffer requirement means initial cycles may use incomplete data.

5. **Settlement Polling Timeout Risk** (Medium): The 300-second (5-minute) timeout for settlement polling creates a race condition. If Polymarket settlement is delayed beyond 5 minutes, the bot may mark a trade as failed while it's still pending, causing state corruption. Overlapping intervals could occur if settlement from interval N completes during interval N+2.

6. **State Persistence Corruption** (Low): While atomic writes (temp file + rename) protect against mid-write crashes, the JSON-based state management has no schema validation or corruption detection. A single malformed write could make `bot_state.json` unreadable, causing the bot to reset to default state and potentially double-spend capital.

7. **Third-Party Dependency Chain** (Medium): Critical dependencies on `ta-lib` (requires system-level installation, not pure Python), `websocket-client`, and external APIs (Binance, Polymarket, CoinGecko) create multiple failure points. The `ta-lib` library is notoriously difficult to install on some systems and may block deployment.

---

## Obstacles

- **No Polymarket API Documentation or Credentials**: The design assumes API endpoints, authentication mechanisms, and market data formats that are currently hypothetical. Without actual API access for testing, the entire execution and market data modules cannot be validated until production deployment.

- **Lack of Backtesting Infrastructure**: The PRD explicitly excludes backtesting as a non-goal, but this means the prediction engine logic (RSI/MACD thresholds, order book imbalance ratios) is untested against historical BTC 5-minute data. No way to validate expected win rate or drawdown characteristics before risking real capital.

- **TA-Lib System Dependency**: The `ta-lib` library requires compilation of C extensions and system-level dependencies (numpy, build tools). This complicates containerization and may cause deployment failures on systems without build toolchains. Pure-Python alternatives (like `pandas-ta`) are not specified.

- **5-Minute Market Availability Uncertainty**: The bot assumes BTC 5-minute directional markets are continuously available on Polymarket for 90 minutes straight. If markets have gaps, close early, or have insufficient liquidity, the bot will skip intervals or fail to execute trades, invalidating the 18-trade assumption.

---

## Assumptions

1. **Polymarket API matches hypothetical specification**: The design assumes REST endpoints for market discovery (`/markets`), order placement (`/orders`), and settlement polling (`/orders/{id}`) with specific request/response formats. **Validation**: Obtain official Polymarket API documentation and verify endpoint contracts before implementation.

2. **BTC 5-minute markets settle deterministically within 5 minutes**: The bot assumes each 5-minute market settles exactly at the interval boundary with WIN/LOSS outcome available immediately. **Validation**: Monitor actual Polymarket BTC markets for settlement timing patterns and edge cases (ties, cancellations, delays).

3. **Binance WebSocket provides sufficient history for indicators**: The system assumes 100 1-minute candles are available from Binance WebSocket buffer to calculate RSI(14) and MACD(12,26,9) accurately from the first interval. **Validation**: Test WebSocket connection initialization and verify minimum data availability before first trade.

4. **Deterministic signals have positive expected value**: The prediction logic assumes RSI/MACD/order book thresholds will produce >50% win rate over 18 trades. **Validation**: Backtest signal logic against historical BTC 5-minute data to measure win rate, drawdown, and Sharpe ratio.

5. **State persistence survives all failure modes**: The design assumes atomic file writes prevent corruption and that `bot_state.json` can always be read on restart. **Validation**: Implement schema validation with Pydantic models and add corruption detection with checksums or version numbers.

---

## Mitigations

### Risk 1: Polymarket API Availability and Stability
- **Action 1.1**: Before implementation, create a standalone API exploration script to test real Polymarket endpoints, authentication, and response formats. Document actual API behavior vs assumptions.
- **Action 1.2**: Implement comprehensive retry logic with exponential backoff (already specified) but add circuit breaker pattern: after 3 consecutive API failures, halt trading rather than continuing with stale data.
- **Action 1.3**: Add API response validation layer that checks schema of all responses before processing. Log discrepancies and halt on critical mismatches.
- **Action 1.4**: Build a mock Polymarket API server for local testing that simulates various failure modes (timeouts, rate limits, malformed responses).

### Risk 2: Technical Indicator Signal Quality
- **Action 2.1**: Implement a dry-run mode (already mentioned in LLD) that logs predictions against real market outcomes without placing trades. Run for multiple 90-minute windows to collect win rate data.
- **Action 2.2**: Add confidence threshold filtering: only execute trades when confidence score exceeds 0.8 (vs current 0.75), reducing number of marginal signals.
- **Action 2.3**: Extend prediction engine to check for "skip conditions": if BTC is in tight range (<1% 30-min movement), force SKIP regardless of indicators to avoid false signals.
- **Action 2.4**: Post-deployment, log all prediction inputs (RSI, MACD, order book values) alongside outcomes to enable offline strategy refinement.

### Risk 3: Win-Streak Capital Scaling Risk
- **Action 3.1**: Add dynamic position sizing cap based on current capital: `max_position = min($25, current_capital * 0.2)` to prevent over-concentration as capital declines.
- **Action 3.2**: Implement "profit lock" rule: after win streak >= 3, reduce multiplier to 1.2x instead of 1.5x to protect accumulated gains.
- **Action 3.3**: Add early shutdown trigger: if capital drops below $50 (50% drawdown vs 30% threshold), halt immediately rather than waiting for 30% limit.
- **Action 3.4**: Log Kelly Criterion calculations alongside position sizes to identify when bet sizing exceeds optimal leverage.

### Risk 4: WebSocket Connection Stability
- **Action 4.1**: Implement pre-flight check: before first trade, verify Binance WebSocket has accumulated minimum 50 candles for indicator calculation. Delay trading start if needed.
- **Action 4.2**: Add WebSocket health monitoring: track last message timestamp and reconnect proactively if no data received for 30 seconds.
- **Action 4.3**: Enhance CoinGecko fallback: cache last known good Binance prices and use weighted average of CoinGecko + cached data to smooth out latency spikes.
- **Action 4.4**: Extend price buffer to 150 candles (vs 100) to provide cushion during reconnection scenarios.

### Risk 5: Settlement Polling Timeout Risk
- **Action 5.1**: Increase settlement polling timeout to 420 seconds (7 minutes) to account for delayed settlements beyond interval boundary.
- **Action 5.2**: Add settlement status tracking: if trade from interval N is still PENDING at start of interval N+1, skip N+1 trade to prevent overlaps.
- **Action 5.3**: Implement settlement reconciliation: after bot completes 18 cycles, poll all order IDs one final time to catch late settlements and update final state.
- **Action 5.4**: Log settlement timing metrics: track actual settlement duration for each trade to identify patterns and adjust timeout dynamically.

### Risk 6: State Persistence Corruption
- **Action 6.1**: Replace plain dataclasses with Pydantic models for `BotState`, `Trade`, and all persisted objects to enforce schema validation on read/write.
- **Action 6.2**: Implement state file versioning: add `"schema_version": "1.0"` field and reject reads of mismatched versions.
- **Action 6.3**: Add backup state files: on each save, keep last 3 versions (`bot_state.json`, `bot_state.json.bak1`, `bot_state.json.bak2`) for manual recovery.
- **Action 6.4**: Pre-deployment test: corrupt state file manually and verify bot detects corruption and fails gracefully with clear error message.

### Risk 7: Third-Party Dependency Chain
- **Action 7.1**: Replace `ta-lib` with pure-Python alternative `pandas-ta` to eliminate C compilation dependency and simplify Docker builds.
- **Action 7.2**: Pin all dependencies to exact versions in `requirements.txt` (use `==` not `>=`) to prevent breaking changes from upstream updates.
- **Action 7.3**: Create Docker image with all dependencies pre-installed and test full build/run cycle in CI before production deployment.
- **Action 7.4**: Add startup validation: verify all required libraries import successfully and external APIs are reachable before entering trading loop.

---

## Appendix: Plan Documents

### PRD
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
- FR-004: Calculate RSI (14-period), MACD (12,26,9), and order book imbalance from data inputs
- FR-005: Generate UP prediction if RSI<30 AND MACD bullish crossover, DOWN if RSI>70 AND MACD bearish crossover
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

### HLD
# High-Level Design: simple-spaghetti-repo

**Created:** 2026-02-16T16:06:43Z
**Status:** Draft

## 1. Architecture Overview

Single-process monolithic application with event-driven loop architecture. The bot runs as a standalone Python process orchestrating four primary modules: Market Data Ingestion, Prediction Engine, Trade Execution, and Risk Manager. Main control loop iterates every 5 minutes for 90 minutes (18 cycles), triggering sequential pipeline: data fetch → prediction → risk check → trade execution → logging. State persists to local JSON files after each cycle for crash recovery.

---

## 2. System Components

**Main Orchestrator**: Event loop managing 5-minute interval timing, component coordination, and graceful shutdown on drawdown breach or completion.

**Market Data Service**: Fetches BTC price data from Binance WebSocket, calculates technical indicators (RSI, MACD), retrieves Polymarket odds via REST API.

**Prediction Engine**: Deterministic rule-based signal generator. Inputs: RSI(14), MACD(12,26,9), order book imbalance. Outputs: UP/DOWN/SKIP decision.

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
- rsi_14: float
- macd_line: float
- macd_signal: float
- order_book_imbalance: float
- polymarket_odds_up: float
- polymarket_odds_down: float

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
- FR-004: Calculate RSI (14-period), MACD (12,26,9), and order book imbalance from data inputs
- FR-005: Generate UP prediction if RSI<30 AND MACD bullish crossover, DOWN if RSI>70 AND MACD bearish crossover
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

### LLD
# Low-Level Design: simple-spaghetti-repo

**Created:** 2026-02-16T16:08:19Z
**Status:** Draft

## 1. Implementation Overview

The Polymarket bot is implemented as a standalone Python application in a new `polymarket-bot/` directory. The system uses a single-threaded event loop architecture that executes every 5 minutes for 18 cycles. Core components include: (1) `main.py` orchestrator managing the event loop and shutdown conditions, (2) `market_data.py` service integrating Binance WebSocket and Polymarket API, (3) `prediction.py` engine implementing RSI/MACD-based signals, (4) `risk.py` controller enforcing drawdown and volatility limits, (5) `capital.py` allocator calculating win-streak position sizing, (6) `execution.py` module submitting orders to Polymarket, and (7) `state.py` persistence layer for JSON logging. Configuration is managed via `.env` file with no external database dependencies.

---

## 2. File Structure

```
polymarket-bot/
├── __init__.py                  # Package marker
├── main.py                      # Event loop orchestrator and entry point
├── config.py                    # Configuration loader from environment variables
├── models.py                    # Data classes for BotState, Trade, Position, MarketData
├── market_data.py               # Market data service (Binance + Polymarket integration)
├── prediction.py                # Prediction engine with RSI/MACD signal logic
├── risk.py                      # Risk controller for drawdown and volatility checks
├── capital.py                   # Capital allocator with win-streak scaling
├── execution.py                 # Trade execution module for Polymarket API
├── state.py                     # State persistence to JSON files
├── utils.py                     # Helper functions for retries and validation
├── .env.example                 # Template for environment variables
├── requirements.txt             # Python dependencies
├── Dockerfile                   # Optional containerization
├── README.md                    # Setup and execution instructions
└── tests/
    ├── __init__.py
    ├── test_prediction.py       # Unit tests for prediction logic
    ├── test_risk.py             # Unit tests for risk controls
    ├── test_capital.py          # Unit tests for position sizing
    ├── test_integration.py      # Integration tests for full pipeline
    └── conftest.py              # pytest fixtures

data/                            # Created at runtime
├── bot_state.json               # Persistent bot state
├── trades.log                   # JSON log of all trades
└── metrics.log                  # Performance metrics per cycle
```

**Modified Files:** None (all new implementation in `polymarket-bot/`)

---

## 3. Detailed Component Designs

### 3.1 Main Orchestrator (`main.py`)

**Responsibilities:** Event loop management, component initialization, shutdown handling

**Key Functions:**
- `main()`: Entry point, initializes components, runs 18-cycle loop
- `run_trading_cycle(interval_number: int) -> bool`: Executes single 5-minute cycle, returns False on critical failure
- `shutdown(reason: str)`: Logs shutdown reason, saves final state

**Control Flow:**
1. Load configuration and validate API connectivity
2. Restore state from `bot_state.json` if exists
3. Loop 18 times with 5-minute sleep intervals
4. Each iteration: fetch data → predict → check risk → allocate capital → execute → log
5. Exit on completion or drawdown breach

### 3.2 Market Data Service (`market_data.py`)

**Responsibilities:** Real-time BTC price from Binance, technical indicators, Polymarket odds retrieval

**Key Classes:**
- `BinanceWebSocketClient`: Manages WebSocket connection, price buffer for indicator calculation
- `PolymarketClient`: REST API wrapper for market discovery and odds fetching

**Key Functions:**
- `get_market_data() -> MarketData`: Aggregates BTC price, RSI, MACD, order book imbalance, Polymarket odds
- `calculate_rsi(prices: List[float], period: int = 14) -> float`: RSI calculation using ta-lib
- `calculate_macd(prices: List[float]) -> Tuple[float, float]`: MACD line and signal line
- `get_order_book_imbalance() -> float`: Binance order book bid/ask ratio
- `find_active_market() -> Optional[str]`: Queries Polymarket for next settling BTC 5-min market

**Error Handling:** Retry logic (3 attempts) for WebSocket disconnects, fallback to CoinGecko if Binance unavailable

### 3.3 Prediction Engine (`prediction.py`)

**Responsibilities:** Deterministic UP/DOWN/SKIP signal generation

**Key Functions:**
- `generate_signal(market_data: MarketData) -> Tuple[str, float]`: Returns ("UP"|"DOWN"|"SKIP", confidence_score)

**Logic:**
```
IF rsi < 30 AND macd_line > macd_signal AND order_book_imbalance > 1.1:
    RETURN ("UP", 0.75)
ELIF rsi > 70 AND macd_line < macd_signal AND order_book_imbalance < 0.9:
    RETURN ("DOWN", 0.75)
ELSE:
    RETURN ("SKIP", 0.0)
```

Confidence score fixed at 0.75 for valid signals, 0.0 for skip. No probabilistic models.

### 3.4 Risk Controller (`risk.py`)

**Responsibilities:** Pre-trade validation, drawdown monitoring, volatility circuit breaker

**Key Functions:**
- `check_drawdown(current_capital: float, starting_capital: float = 100.0) -> bool`: Returns True if drawdown < 30%
- `check_volatility(price_history: List[float]) -> bool`: Returns True if 5-min range < 3%
- `approve_trade(signal: str, market_data: MarketData, bot_state: BotState) -> bool`: Combines all checks

**Drawdown Calculation:** `drawdown = (starting_capital - current_capital) / starting_capital`

**Volatility Check:** `range = (max(last_5_prices) - min(last_5_prices)) / min(last_5_prices)`

### 3.5 Capital Allocator (`capital.py`)

**Responsibilities:** Position sizing with win-streak scaling

**Key Functions:**
- `calculate_position_size(bot_state: BotState) -> float`: Implements base * (1.5 ^ win_streak) capped at $25

**Formula:**
```
base_size = 5.0
multiplier = 1.5
max_size = 25.0
position_size = min(base_size * (multiplier ** bot_state.win_streak), max_size)
```

**Constraints:** Position size never exceeds `current_capital * 0.5` (additional safety check)

### 3.6 Trade Execution (`execution.py`)

**Responsibilities:** Polymarket API order submission, settlement polling

**Key Functions:**
- `submit_order(market_id: str, direction: str, size: float) -> str`: Places market order, returns order_id
- `poll_settlement(order_id: str, timeout: int = 300) -> str`: Waits for settlement, returns "WIN"|"LOSS"

**API Integration:**
- POST `/orders` with `{market_id, side: "YES"|"NO", amount, type: "MARKET"}`
- GET `/orders/{order_id}` every 10 seconds until status = "SETTLED"

**Retry Logic:** Max 3 retries with exponential backoff (2s, 4s, 8s)

### 3.7 State Persistence (`state.py`)

**Responsibilities:** JSON file I/O for bot state and trade logs

**Key Functions:**
- `load_state() -> BotState`: Reads `bot_state.json`, returns default if missing
- `save_state(state: BotState)`: Writes current state atomically
- `log_trade(trade: Trade)`: Appends JSON line to `trades.log`
- `log_metrics(metrics: Dict[str, Any])`: Appends to `metrics.log`

**Atomic Write:** Uses temp file + rename to prevent corruption on crash

---

## 4. Database Schema Changes

**N/A** - No database required. All persistence uses local JSON files.

---

## 5. API Implementation Details

### 5.1 Binance WebSocket API

**Endpoint:** `wss://stream.binance.com:9443/ws/btcusdt@kline_1m`

**Message Handling:**
```python
def on_message(ws, message):
    data = json.loads(message)
    price = float(data['k']['c'])  # Close price
    price_buffer.append(price)
    if len(price_buffer) > 100:
        price_buffer.pop(0)
```

**Connection Management:** Auto-reconnect on disconnect, max 5 retry attempts

### 5.2 Polymarket REST API

**Base URL:** `https://api.polymarket.com/v1` (hypothetical, actual endpoint TBD)

**Authentication:** Bearer token in header
```python
headers = {
    "Authorization": f"Bearer {POLYMARKET_API_KEY}",
    "Content-Type": "application/json"
}
```

**Endpoints:**
1. `GET /markets?asset=BTC&interval=5m&status=active`
   - Response: `[{market_id, odds_yes, odds_no, settlement_time}]`
   
2. `POST /orders`
   - Request: `{market_id, side: "YES"|"NO", amount: float, type: "MARKET"}`
   - Response: `{order_id, status, filled_amount}`

3. `GET /orders/{order_id}`
   - Response: `{order_id, status: "PENDING"|"SETTLED", outcome: "WIN"|"LOSS"}`

**Error Handling:** All 4xx/5xx responses raise `PolymarketAPIError` with retry logic

### 5.3 CoinGecko Fallback API

**Endpoint:** `GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd`

**Usage:** Only if Binance WebSocket fails after 3 reconnection attempts

---

## 6. Function Signatures

```python
# models.py
@dataclass
class BotState:
    current_capital: float
    starting_capital: float = 100.0
    win_streak: int = 0
    total_trades: int = 0
    is_active: bool = True

@dataclass
class Trade:
    timestamp: str
    interval_number: int
    prediction: str
    odds: float
    position_size: float
    outcome: str
    pnl: float
    capital_after: float

@dataclass
class Position:
    direction: str
    entry_time: str
    settlement_time: str
    size: float
    status: str

@dataclass
class MarketData:
    btc_price: float
    rsi_14: float
    macd_line: float
    macd_signal: float
    order_book_imbalance: float
    polymarket_odds_up: float
    polymarket_odds_down: float

# main.py
def main() -> None
def run_trading_cycle(interval_number: int) -> bool
def shutdown(reason: str) -> None

# market_data.py
class BinanceWebSocketClient:
    def connect(self) -> None
    def get_latest_prices(self, count: int = 100) -> List[float]
    def close(self) -> None

class PolymarketClient:
    def __init__(self, api_key: str, api_secret: str)
    def find_active_market(self) -> Optional[str]
    def get_market_odds(self, market_id: str) -> Tuple[float, float]

def get_market_data() -> MarketData
def calculate_rsi(prices: List[float], period: int = 14) -> float
def calculate_macd(prices: List[float]) -> Tuple[float, float]
def get_order_book_imbalance() -> float

# prediction.py
def generate_signal(market_data: MarketData) -> Tuple[str, float]

# risk.py
def check_drawdown(current_capital: float, starting_capital: float = 100.0) -> bool
def check_volatility(price_history: List[float]) -> bool
def approve_trade(signal: str, market_data: MarketData, bot_state: BotState) -> bool

# capital.py
def calculate_position_size(bot_state: BotState) -> float

# execution.py
def submit_order(market_id: str, direction: str, size: float) -> str
def poll_settlement(order_id: str, timeout: int = 300) -> str

# state.py
def load_state() -> BotState
def save_state(state: BotState) -> None
def log_trade(trade: Trade) -> None
def log_metrics(metrics: Dict[str, Any]) -> None

# utils.py
def retry(func: Callable, max_attempts: int = 3, backoff: float = 2.0) -> Any
def validate_price(price: float) -> bool
def validate_odds(odds: float) -> bool
```

---

## 7. State Management

**State Storage:** All state persists to `data/bot_state.json` as JSON. In-memory state managed via `BotState` dataclass instance.

**State Updates:** After each trade settlement:
1. Update `current_capital` with PnL
2. Increment/reset `win_streak` based on outcome
3. Increment `total_trades`
4. Call `save_state()` to persist

**Crash Recovery:** On startup, `load_state()` checks for existing `bot_state.json`. If found and `is_active=True`, resume from last interval. If `total_trades >= 18`, exit immediately.

**Concurrency:** None required (single-threaded). No locking mechanisms needed.

---

## 8. Error Handling Strategy

### Error Categories

**Critical Errors (halt trading):**
- `MaxDrawdownExceeded`: Drawdown >= 30%
- `InsufficientCapital`: Current capital < minimum position size ($5)
- `APIAuthenticationFailure`: Invalid Polymarket credentials

**Recoverable Errors (skip interval):**
- `BinanceConnectionError`: WebSocket disconnect (fallback to CoinGecko)
- `PolymarketAPIError`: Rate limit or temporary outage
- `NoActiveMarket`: No BTC 5-min market available

**Validation Errors:**
- `InvalidPriceData`: Price <= 0 or > 1,000,000
- `InvalidOdds`: Odds <= 0 or > 1

### Error Response Format

```python
class BotError(Exception):
    """Base exception with error code and user message"""
    def __init__(self, code: str, message: str, recoverable: bool = False):
        self.code = code
        self.message = message
        self.recoverable = recoverable
```

### Logging Strategy

All errors logged with:
```json
{
  "timestamp": "2026-02-16T16:30:00Z",
  "level": "ERROR|CRITICAL",
  "component": "risk|market_data|execution",
  "error_code": "MAX_DRAWDOWN_EXCEEDED",
  "message": "Trading halted: drawdown 32% exceeds 30% limit",
  "interval": 12
}
```

---

## 9. Test Plan

### Unit Tests

**test_prediction.py:**
- `test_generate_signal_up()`: RSI=25, MACD bullish → "UP"
- `test_generate_signal_down()`: RSI=75, MACD bearish → "DOWN"
- `test_generate_signal_skip()`: RSI=50, neutral → "SKIP"
- `test_confidence_scores()`: Valid signals return 0.75

**test_risk.py:**
- `test_drawdown_within_limit()`: $75 capital → approved
- `test_drawdown_exceeds_limit()`: $69 capital → rejected
- `test_volatility_normal()`: 2% range → approved
- `test_volatility_excessive()`: 4% range → rejected

**test_capital.py:**
- `test_base_position_no_streak()`: win_streak=0 → $5
- `test_position_with_streak()`: win_streak=2 → $11.25
- `test_position_cap()`: win_streak=5 → $25 (capped)

**test_state.py:**
- `test_save_and_load_state()`: Roundtrip persistence
- `test_atomic_write()`: No corruption on simulated crash
- `test_log_trade_append()`: Multiple trades logged correctly

### Integration Tests

**test_integration.py:**
- `test_full_trading_cycle()`: Mock APIs, verify complete pipeline from data fetch to state update
- `test_win_streak_flow()`: Simulate 3 wins, verify position scaling
- `test_loss_resets_streak()`: Win → Win → Loss → verify streak=0
- `test_drawdown_halt()`: Simulate losses until 30% drawdown, verify shutdown
- `test_api_retry_logic()`: Mock transient API failure, verify retry success
- `test_fallback_price_source()`: Binance down → CoinGecko used

### E2E Tests

**test_e2e_full_run.py:**
- `test_18_cycle_completion()`: Run full 90-minute simulation with mocked APIs, verify 18 trades logged
- `test_crash_recovery()`: Kill process at interval 10, restart, verify resume from correct state

**Manual Testing Checklist:**
1. API connectivity validation (Binance, Polymarket, CoinGecko)
2. Real API call with small position ($1) to verify order flow
3. Log file integrity after forced shutdown
4. Docker container execution

---

## 10. Migration Strategy

**Step 1: Repository Setup**
- Create `polymarket-bot/` directory in repository root
- Add `.env.example` with placeholder API keys
- Update root `requirements.txt` to include: `websocket-client==1.6.4`, `ta-lib==0.4.28`, `python-dotenv==1.0.0`

**Step 2: Environment Configuration**
- Copy `.env.example` to `.env`
- Obtain Polymarket API credentials (requires account signup)
- Add Binance and CoinGecko API keys (optional for fallback)

**Step 3: Dependency Installation**
```bash
pip install -r polymarket-bot/requirements.txt
```

**Step 4: Initial Validation**
- Run `python -m polymarket_bot.market_data` standalone to test API connectivity
- Verify `data/` directory created with correct permissions

**Step 5: Dry Run**
- Execute `python -m polymarket_bot.main --dry-run` (no real orders, log only)
- Review `trades.log` for expected 18 entries

**Step 6: Production Run**
- Remove `--dry-run` flag
- Monitor first 3 intervals manually
- Verify trades appearing on Polymarket dashboard

**No existing code modification required** - bot is self-contained module.

---

## 11. Rollback Plan

**Scenario 1: Critical Bug Discovered Mid-Run**
- Process auto-halts on unhandled exception
- State persisted at last successful interval
- Manual review of `bot_state.json` to assess capital impact
- No rollback needed (state immutable)

**Scenario 2: API Credential Compromise**
- Rotate Polymarket API keys via dashboard
- Update `.env` file
- Restart bot (will load new credentials)

**Scenario 3: Incorrect Position Sizing**
- Bot completes run (no mid-flight cancellation to avoid inconsistent state)
- Post-run analysis of `trades.log` to calculate actual loss
- Code fix deployed for next execution

**Data Rollback:** Not applicable (no database). Trade logs append-only, cannot be "rolled back". Manual reconciliation with Polymarket order history if discrepancies found.

**Code Rollback:**
```bash
git revert <commit-hash>
git push origin main
```

No infrastructure dependencies to roll back (stateless application).

---

## 12. Performance Considerations

**Execution Time Budget:**
- Target cycle time: <60 seconds (leaves 4 minutes buffer per 5-min interval)
- Breakdown: Data fetch (5s) → Indicators (2s) → Prediction (0.1s) → Order submission (3s) → Total ~10s

**Caching Strategy:**
- Price buffer maintained in-memory (last 100 1-min candles) for indicator calculation
- No external cache needed (Redis, Memcached) given single-instance deployment

**API Rate Limits:**
- Binance WebSocket: No rate limit (streaming)
- Polymarket: Assumed 60 req/min (within budget: 18 intervals = ~6 req/min)
- CoinGecko: 50 req/min (fallback only)

**Memory Footprint:**
- Price buffer: 100 floats × 8 bytes = 800 bytes
- State objects: <1 KB
- Expected peak RAM: <50 MB

**Optimization Opportunities:**
1. Pre-calculate indicators incrementally (update on new price vs recalculate full window)
2. Parallel API calls (fetch Polymarket odds while calculating indicators)
3. Connection pooling for HTTP requests (reuse session)

**Not Implemented (YAGNI):**
- Database indexing (no database)
- CDN for static assets (no frontend)
- Load balancing (single instance)

---

## Appendix: Existing Repository Structure

## Repository File Structure

```
.claude-plan.json
.claude-resolution.json
.conflict-info.json
.eslintrc.cjs
.git
.gitignore
.pr-number
.review-feedback.txt
README.md
api/
  __init__.py
  app.py
  audit_service.py
  auth.py
  config.py
  create_admin.py
  data_store.py
  database.py
  main.py
  middleware/
    __init__.py
    auth_middleware.py
  migrations/
    001_initial_schema.py
  models/
    __init__.py
    circuit.py
    driver.py
    prediction.py
    prediction_accuracy.py
    qualifying_result.py
    race.py
    race_result.py
    team.py
    token.py
    user.py
    weather_data.py
  routes/
    __init__.py
    auth.py
    protected.py
  services/
    __init__.py
    auth_service.py
    user_repository.py
  test_voting_implementation.py
  utils/
    __init__.py
    csrf_protection.py
    jwt_manager.py
    password.py
    rate_limiter.py
    sanitizer.py
  validators.py
  voting/
    __init__.py
    admin_routes.py
    data_store.py
    middleware.py
    models.py
    routes.py
    services.py
dist/
  assets/
    index-BbtGegjc.js
    index-BjzYgeXi.css
    index-C9Es-Unh.css
    index-CSdvkKiq.js
    index-D9FKnH8Y.css
    index-DH9HE5kx.js
  index.html
docs/
  CI-CD-IMPLEMENTATION.md
  F1_DATABASE_MODELS.md
  F1_DATA_INGESTION.md
  F1_MONITORING_GUIDE.md
  KUBERNETES_DEPLOYMENT.md
  SECURE_DEPLOYMENT.md
  SECURITY_CHECKLIST.md
  concepts/
    cool-penguin-page/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    f1-prediction-analytics/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      infrastructure.md
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    happy-llama-page/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    library-api/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    orange-background-minimax/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    pasta-recipes-react/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    pigeon-website/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    polymarket-bot/
      HLD.md
      LLD.md
      PRD.md
      README.md
      ROAM.md
      epic.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    pta-voting-system/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    python-auth-api/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    red-background-claude/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
  data-transformation-validation.md
  f1-analytics-database-schema.md
  monitoring/
    alertmanager-configuration.md
  plans/
    simple-spaghetti-website/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
    test-pizza-page/
      HLD.md
      LLD.md
      PRD.md
      ROAM.md
      epic.yaml
      issues_created.yaml
      slices.yaml
      tasks.yaml
      timeline.md
      timeline.yaml
f1-analytics/
  .env.example
  .env.production.template
  .env.template
  .gitignore
  PRODUCTION_SECURITY.md
  README.md
  backend/
    .env.example
    Dockerfile
    README.md
    alembic/
      env.py
      script.py.mako
      versions/
        001_initial_f1_analytics_schema.py
        001_initial_f1_schema.py
        001_initial_schema.py
    alembic.ini
    app/
      __init__.py
      config.py
      core/
        __init__.py
        config.py
        exceptions.py
        middleware.py
        security.py
      database.py
      dependencies.py
      ingestion/
        __init__.py
        base.py
        cli.py
        config.py
        qualifying_ingestion.py
        race_ingestion.py
      main.py
      middleware/
        __init__.py
      models/
        __init__.py
        circuit.py
        driver.py
        f1_models.py
        prediction.py
        prediction_accuracy.py
        qualifying_result.py
        race.py
        race_result.py
        team.py
        user.py
        weather_data.py
      monitoring/
        __init__.py
        metrics.py
        middleware.py
        services.py
      repositories/
        __init__.py
        base.py
        f1_repositories.py
        user_repository.py
      routes/
        __init__.py
      schemas/
        __init__.py
        base.py
        driver.py
        prediction.py
        race.py
        team.py
      services/
        __init__.py
        base.py
        driver_service.py
        prediction_service.py
        race_service.py
      utils/
        __init__.py
        jwt_manager.py
        session_manager.py
        transformers.py
        validators.py
    pyproject.toml
    pytest.ini
    requirements.txt
    test_models.py
    test_syntax.py
    tests/
      __init__.py
      conftest.py
      test_config.py
      test_database.py
      test_health_checks.py
      test_ingestion.py
      test_main.py
      test_security.py
      test_session_management.py
      test_validation_layer.py
      unit/
        __init__.py
        test_models.py
        test_monitoring.py
    validate_monitoring.py
    validate_syntax.sh
    verify_schema.py
  frontend/
    Dockerfile
    index.html
    nginx.conf
    package.json
    public/
      health
    src/
      App.css
      App.tsx
      index.css
      main.tsx
      tests/
        App.test.tsx
        setup.ts
    tailwind.config.js
    vite.config.test.ts
    vite.config.ts
  infrastructure/
    docker-compose.prod.yml
    docker-compose.yml
    init-scripts/
      01-init-database.sql
    monitoring/
      grafana-dashboard-configmap.yaml
      grafana-dashboards/
        ml-pipeline.json
        system-health.json
      prometheus-config.yaml
      prometheus.yml
    nginx/
      nginx.prod.conf
    terraform/
      .gitignore
      README.md
      main.tf
      modules/
        eks/
          main.tf
          outputs.tf
          variables.tf
        elasticache/
          main.tf
          outputs.tf
          variables.tf
        monitoring/
          main.tf
          outputs.tf
          variables.tf
        rds/
          main.tf
          outputs.tf
          variables.tf
        s3/
          main.tf
          outputs.tf
          variables.tf
        vpc/
          main.tf
          outputs.tf
          variables.tf
      outputs.tf
      scripts/
        deploy.sh
      terraform.tfvars.example
      variables.tf
  scripts/
    dev_commands.sh
    generate_secrets.sh
    init_dev.sh
    test_environment.sh
hello-world.html
index.html
infrastructure/
  kubernetes/
    airflow-deployment.yaml
    api-gateway-deployment.yaml
    configmaps.yaml
    environments/
      development/
        domains.yaml
      production/
        domains.yaml
        image-tags.yaml
        ingress.yaml
      staging/
        domains.yaml
        ingress.yaml
    external-secrets/
      README.md
      aws-iam-role.yaml
      aws-secret-store.yaml
      external-secrets-operator.yaml
      external-secrets.yaml
    frontend-deployment.yaml
    ingress.yaml
    namespace.yaml
    network-policies.yaml
    postgres-config.yaml
    postgres-statefulset.yaml
    prediction-service-deployment.yaml
    redis-config.yaml
    redis-deployment.yaml
    secrets.yaml
  monitoring/
    alertmanager-rules.yaml
    alertmanager-secrets.yaml
    exporters.yaml
    grafana.yaml
    prometheus.yaml
    validate-alerts.sh
package-lock.json
package.json
postcss.config.js
requirements.txt
scripts/
  deploy.sh
  ingest_f1_data.py
  validate-security.sh
spaghetti.html
src/
  App.css
  App.jsx
  components/
    BallotCard.jsx
    FilterPanel.jsx
    LoginForm.jsx
    Navigation.jsx
    RecipeCard.jsx
    RecipeDetail.jsx
    RecipeList.jsx
    SearchBar.jsx
    VotingPage.jsx
  context/
    RecipeContext.jsx
    VotingContext.jsx
  data/
    recipes.json
  index.css
  main.jsx
  utils/
    filterHelpers.js
  voting/
    App.jsx
    api/
      votingApi.js
    components/
      CandidateCard.jsx
    context/
      AuthContext.jsx
    pages/
      VoterLogin.jsx
      admin/
        AuditLogs.jsx
        CandidateManagement.jsx
        Dashboard.jsx
        ElectionManagement.jsx
tailwind.config.js
test_admin_endpoints.py
test_admin_implementation.py
test_auth_implementation.py
test_data_store_validators.py
test_election_management.py
test_f1_models.py
test_imports.py
test_library_api.py
test_loan_implementation.py
test_member_registration.py
test_models.py
test_pta_voting_system.py
test_security_fixes.py
test_voting_api.py
test_voting_authentication.py
test_voting_middleware.py
test_voting_middleware_simple.py
validate_html.sh
validate_implementation.md
verify_voting_system.py
vite.config.js
```