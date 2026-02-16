# ROAM Analysis: polymarket-bot

**Feature Count:** 8
**Created:** 2026-02-16T16:11:51Z

## Risks

1. **Polymarket API Availability and Documentation** (High): The LLD references a hypothetical Polymarket API endpoint (`https://api.polymarket.com/v1`) with "actual endpoint TBD". Polymarket's actual API structure, authentication mechanism, market discovery endpoints, order placement flow, and settlement polling may differ significantly from assumptions. The bot's core trading functionality depends entirely on this integration working correctly.

2. **5-Minute Market Availability** (High): The entire strategy assumes BTC 5-minute directional markets are consistently available on Polymarket for 18 consecutive intervals. If such markets don't exist, are illiquid, or have irregular settlement times, the bot cannot execute its core function. Market availability, liquidity depth, and odds quality are unknown.

3. **Technical Indicator Signal Quality** (Medium): The deterministic prediction logic using RSI < 30 / > 70 with MACD crossovers is a well-known retail trading strategy that may have poor win rates in efficient markets. The strategy assumes these indicators provide edge in 5-minute BTC prediction, but no backtesting validates this assumption. Poor signal quality could lead to rapid capital depletion.

4. **WebSocket Connection Stability** (Medium): The Binance WebSocket client maintains a price buffer critical for indicator calculation. Connection drops, message delays, or reconnection failures during the 90-minute window could result in stale data feeding into predictions. The 100-candle buffer requires ~100 minutes of historical data on startup, which may not be available if starting fresh.

5. **Win-Streak Amplification Risk** (Medium): The 1.5x multiplier per win can rapidly increase position sizes (base $5 → $11.25 → $16.88 → $25). A lucky early streak followed by losses at maximum position size could trigger the 30% drawdown limit prematurely. The strategy is vulnerable to variance despite the $25 cap.

6. **Settlement Timing and Slippage** (Medium): The bot must submit orders before each 5-minute interval closes and wait for settlement to know outcomes. Settlement delays, rejected orders, or partial fills could disrupt the sequential 18-interval execution model. The polling mechanism (`poll_settlement` with 300s timeout) may not align with actual Polymarket settlement speeds.

7. **Third-Party Dependency Failures** (Low): The bot relies on ta-lib for indicator calculation, which requires system-level dependencies and can be difficult to install. Binance and CoinGecko APIs, while reliable, could rate-limit or change endpoints during execution. The fallback logic assumes CoinGecko provides comparable data quality.

---

## Obstacles

- **Polymarket API Credentials and Access**: No documented process for obtaining Polymarket API keys. The platform may require KYC, minimum deposits, or restrict programmatic trading access. API access may not be publicly available.

- **Ta-lib Installation Complexity**: The ta-lib library requires C dependencies that are notoriously difficult to install on some systems (especially macOS and Windows). This could block development and testing if not addressed with clear setup documentation or Docker-only deployment.

- **Lack of Dry-Run Infrastructure**: While the LLD mentions a `--dry-run` flag, there's no implementation detail for mocking Polymarket order placement. Without this, testing the full 18-cycle flow requires real capital at risk.

- **5-Minute Execution Timing**: The bot must complete data fetch → prediction → order submission within each 5-minute window while leaving buffer time for settlement. Tight timing constraints with external API dependencies create execution risk.

---

## Assumptions

1. **Polymarket offers programmatic API access** with endpoints for market discovery, order placement, and settlement tracking similar to traditional exchanges. *Validation: Research Polymarket API documentation and developer portal before implementation.*

2. **BTC 5-minute directional markets exist and settle reliably** on Polymarket with sufficient liquidity for $5-$25 positions. *Validation: Manual inspection of Polymarket platform to confirm market availability and settlement history.*

3. **Binance WebSocket provides sufficient historical data** on connection to populate the 100-candle buffer needed for indicator calculation. *Validation: Test WebSocket client initialization and verify initial data payload structure.*

4. **The 30% max drawdown threshold is sufficient** to prevent total capital loss while allowing the strategy to weather normal losing streaks. *Validation: Monte Carlo simulation of strategy with varying win rates (40-60%) to test drawdown distribution.*

5. **Settlement completes within 5 minutes** of each interval closing, allowing sequential non-overlapping trades. *Validation: Monitor actual Polymarket settlement times for 5-minute BTC markets if available.*

6. **RSI/MACD signals generated from 1-minute Binance candles are applicable** to Polymarket 5-minute outcomes despite different market structures (spot exchange vs prediction market). *Validation: None possible without backtesting; accept as experimental premise.*

---

## Mitigations

### Risk 1: Polymarket API Availability and Documentation
- **Action 1.1**: Conduct upfront research sprint to locate official Polymarket API documentation, SDKs, or developer community resources before writing any integration code.
- **Action 1.2**: If official API doesn't exist, explore alternative implementations: (a) Polymarket CLOB (Central Limit Order Book) integration if available, (b) Gamma Markets API if compatible, or (c) pivot to a different prediction market platform with documented APIs (e.g., Augur, Gnosis).
- **Action 1.3**: Build a mock Polymarket API server for testing that simulates market discovery, order placement, and settlement responses based on assumed schema from LLD.

### Risk 2: 5-Minute Market Availability
- **Action 2.1**: Before full implementation, manually verify on Polymarket UI that BTC 5-minute markets exist, their typical liquidity levels, and historical settlement reliability.
- **Action 2.2**: Add market discovery validation to bot startup checks: if no active 5-min BTC market found, log critical error and exit immediately rather than proceeding.
- **Action 2.3**: Implement flexible interval configuration to allow fallback to 10-minute or 15-minute markets if 5-minute markets prove unreliable (requires PRD adjustment).

### Risk 3: Technical Indicator Signal Quality
- **Action 3.1**: Accept this as experimental risk inherent to the project scope. Document clearly in README that the strategy is for educational/experimental purposes, not production trading.
- **Action 3.2**: Implement comprehensive trade logging (already planned) to enable post-mortem analysis of signal performance.
- **Action 3.3**: Add configurable prediction thresholds (RSI levels, MACD crossover sensitivity) via environment variables to allow rapid iteration without code changes.

### Risk 4: WebSocket Connection Stability
- **Action 4.1**: Implement aggressive reconnection logic with exponential backoff (already planned: max 5 retry attempts). Add connection health monitoring with heartbeat checks.
- **Action 4.2**: Persist the last 100 price points to `price_buffer.json` after each update, allowing the bot to restore buffer state after crash/restart instead of requiring 100 minutes of fresh data.
- **Action 4.3**: If WebSocket fails, immediately fallback to Binance REST API `/api/v3/klines` endpoint to fetch historical 1-minute candles and populate buffer, then switch to polling mode (1-minute interval requests).

### Risk 5: Win-Streak Amplification Risk
- **Action 5.1**: Current design already caps position size at $25 (25% of capital), which limits single-trade loss exposure. Maintain this cap.
- **Action 5.2**: Add simulation mode to model capital trajectories under different win-rate scenarios (45%, 50%, 55%) before live deployment to validate 30% drawdown threshold adequacy.
- **Action 5.3**: Consider implementing a "cool-down" mechanism: after reaching max position size ($25), require 2 consecutive wins at max size before continuing, reducing variance exposure.

### Risk 6: Settlement Timing and Slippage
- **Action 6.1**: Build in 60-second buffer before interval close for order submission. If current time is within 60s of next interval start, skip the trade to avoid race conditions.
- **Action 6.2**: Extend `poll_settlement` timeout to 600 seconds (10 minutes) to accommodate slow settlement, and add exponential backoff polling (start at 5s intervals, increase to 30s).
- **Action 6.3**: Implement partial fill handling: if order partially fills, record actual filled amount and adjust position sizing calculations accordingly rather than assuming full fills.

### Risk 7: Third-Party Dependency Failures
- **Action 7.1**: Provide Docker-based deployment as primary method (Dockerfile already planned) with pre-built ta-lib binaries in the image to eliminate installation issues.
- **Action 7.2**: Add `requirements.txt` with pinned versions for all dependencies to ensure reproducible builds. Include alternative pure-Python indicator implementations as fallback if ta-lib import fails.
- **Action 7.3**: Implement rate limit handling for Binance (unlikely given WebSocket) and CoinGecko (50 req/min): add request throttling and exponential backoff on 429 responses.

### Obstacle: Polymarket API Credentials and Access
- **Action O.1**: Immediate task: Create Polymarket account and navigate platform to locate API access settings or developer documentation.
- **Action O.2**: If API access requires approval/waitlist, submit application immediately and prepare to adjust timeline or use testnet if available.
- **Action O.3**: Document all credential requirements, KYC steps, and deposit minimums in setup README to unblock future users.

### Obstacle: Ta-lib Installation Complexity
- **Action O.4**: Make Docker deployment the primary/only supported deployment method to sidestep system-level dependency issues.
- **Action O.5**: Add fallback to `pandas-ta` library (pure Python) if ta-lib import fails, with feature parity for RSI and MACD calculations.

### Obstacle: Lack of Dry-Run Infrastructure
- **Action O.6**: Implement `--dry-run` mode in `execution.py` that logs intended orders without API calls, returns mock order IDs, and simulates random WIN/LOSS outcomes with 50% probability for testing.
- **Action O.7**: Create integration test fixtures with recorded API responses for full end-to-end testing without live API dependencies.

### Obstacle: 5-Minute Execution Timing
- **Action O.8**: Optimize data fetch with parallel API calls: fetch Polymarket odds concurrently with indicator calculation using `asyncio` or threading.
- **Action O.9**: Add execution time logging to identify bottlenecks and ensure total cycle time stays under 60s threshold during testing.

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