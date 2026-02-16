# ROAM Analysis: polymarket-bot

**Feature Count:** 12
**Created:** 2026-02-16T15:30:12Z

## Risks

**1. Polymarket API Uncertainty** (High): The design assumes a Polymarket API exists with specific endpoints (`/markets/{market_id}`, `/orders`, `/markets/{market_id}/resolution`) that may not match reality. Polymarket's actual API structure, authentication method, market ID format, and BTC 5-minute directional market availability are unverified. If the API differs significantly or BTC 5-minute markets don't exist, core functionality breaks.

**2. Price Feed Reliability in 5-Minute Windows** (High): The bot depends on continuously receiving BTC price data to populate a 60-point buffer and calculate RSI/EMA indicators. WebSocket disconnections, REST API outages, or price anomaly rejections could leave the bot without sufficient data to generate predictions. A single failed interval is acceptable, but cascading failures could skip multiple trades and invalidate the 18-interval strategy.

**3. Settlement Polling Timeout Risk** (Medium): Markets are polled every 15 seconds for up to 5 minutes (300s) for settlement. If Polymarket settles markets late or the bot's 5-minute window alignment is off, timeouts could prevent accurate P&L calculation and equity updates. This would corrupt the win streak logic and position sizing for subsequent intervals.

**4. Win-Streak Strategy Profitability Assumption** (High): The capital allocation strategy assumes technical indicators (RSI/EMA) can generate positive win streaks frequently enough to compound gains. In reality, BTC 5-minute directional prediction is near-random, and a 50/50 win rate with market odds around 0.50 results in slow capital erosion due to fees. The 30% drawdown stop could trigger before any meaningful gains.

**5. Time Synchronization Drift** (Medium): The bot relies on system time to schedule exact 5-minute intervals. NTP drift >500ms or delayed API calls could cause the bot to submit orders after interval close or fetch stale market data. This introduces timing skew that accumulates over 18 intervals (90 minutes).

**6. State Corruption on Crash During Settlement** (Medium): While atomic file writes protect `bot_state.json`, a crash between settlement detection and state save could lose the last trade outcome. The bot would resume with incorrect equity and win streak, leading to invalid position sizing and potential over-exposure.

**7. Dependency on External Libraries for Indicators** (Low): The bot uses `pandas-ta` for RSI/EMA calculation. If this library has bugs, numerical instability, or unexpected behavior with edge cases (e.g., all prices identical), prediction signals could be incorrect or cause exceptions.

---

## Obstacles

- **No Polymarket API Documentation Available**: As of 2026-02-16, there is no public confirmation of Polymarket API endpoints, authentication mechanism, or whether BTC 5-minute directional markets exist. Development must proceed with mock implementations for testing, and the first production run will validate all API assumptions.

- **30-Minute Price Buffer Initialization Delay**: The bot requires 30 minutes to populate the initial 60-price buffer before generating the first prediction. This means the first trade can only occur after 30 minutes of runtime, leaving only 60 minutes for the remaining 17 intervals. This constraint is not well-documented in the PRD.

- **Unknown Polymarket Market Odds and Fees**: The design assumes market odds around 0.50 for fair pricing, but actual odds, trading fees, and payout calculation logic are unknown. If fees are >5% per trade or odds are heavily skewed, the strategy may not be viable even with a 60% win rate.

- **Testing Without Live API Access**: Comprehensive end-to-end testing requires a working Polymarket API. Without testnet access or production API credentials during development, testing is limited to mocked responses, increasing the risk of integration failures on first live run.

---

## Assumptions

**1. Polymarket API Matches Design Specification**: Assumes Polymarket provides REST endpoints for market data (`GET /markets/{market_id}`), order submission (`POST /orders`), and settlement resolution (`GET /markets/{market_id}/resolution`) with Bearer token authentication. **Validation**: Obtain official Polymarket API documentation or test credentials before implementation; if unavailable, implement configurable API client to adapt to actual endpoints during first run.

**2. BTC 5-Minute Directional Markets Exist and Settle On Time**: Assumes Polymarket offers BTC UP/DOWN contracts that settle exactly every 5 minutes with deterministic outcomes. **Validation**: Manually browse Polymarket platform to confirm market availability and settlement timing; if not available, switch to hourly or daily BTC markets and adjust interval count.

**3. Technical Indicators Provide Edge in 5-Minute BTC Prediction**: Assumes RSI and EMA crossover signals can predict BTC directional moves better than random chance. **Validation**: Backtest RSI/EMA strategy on historical 5-minute BTC data before live deployment; if win rate <52%, consider alternative signals or accept strategy is for learning purposes only.

**4. External Price Feeds Have <1% Downtime**: Assumes Binance WebSocket, Coinbase, and CoinGecko APIs have high availability during the 90-minute trading window. **Validation**: Monitor price feed uptime during test runs; implement aggressive caching (last known price up to 60s old) if downtime exceeds 1%.

**5. System Clock Drift Stays Below 500ms**: Assumes NTP synchronization keeps system time accurate within 500ms throughout the session. **Validation**: Run `chronyc tracking` or `ntpq -p` before each session; add pre-flight check in bot startup to fail if drift exceeds threshold.

---

## Mitigations

**For Risk 1 (Polymarket API Uncertainty):**
- **Pre-Implementation API Discovery**: Before writing code, manually inspect Polymarket's website or contact support to obtain API documentation. If unavailable, use browser DevTools to reverse-engineer API calls from the web interface.
- **Adapter Pattern for API Client**: Implement `MarketConnector` with a pluggable backend (e.g., `PolymarketAPIAdapter`, `MockAPIAdapter`) to quickly swap implementations if real API differs from spec.
- **Graceful Degradation on API Mismatch**: Add startup validation that fetches market metadata and verifies response schema matches expectations; log detailed errors and halt bot if critical fields are missing.

**For Risk 2 (Price Feed Reliability):**
- **Multi-Source Price Aggregation**: Instead of strict fallback, fetch prices from Binance, Coinbase, and CoinGecko simultaneously (if one fails) and use median price to reduce single-source failure impact.
- **Stale Price Tolerance**: Allow prediction engine to use prices up to 90 seconds old if all feeds fail temporarily, rather than skipping the interval entirely.
- **Pre-Flight Buffer Check**: Before each interval, verify price buffer has at least 30 recent points; if buffer is stale (oldest point >10 minutes old), trigger warning and skip interval.

**For Risk 3 (Settlement Polling Timeout):**
- **Extended Timeout with Warning**: Increase settlement polling timeout to 360 seconds (6 minutes) to handle late settlements; log warning if settlement takes >300s to identify timing issues.
- **Fallback to Manual Settlement Check**: If timeout occurs, save trade as "pending" in state and add recovery logic on next startup to check resolution retroactively via API.
- **Settlement Webhook Support**: If Polymarket offers settlement webhooks, replace polling with event-driven settlement detection to eliminate timeout risk.

**For Risk 4 (Win-Streak Strategy Profitability):**
- **Conservative Default-to-SKIP Strategy**: Modify signal rules to skip intervals (no trade) when no strong signal (RSI <30 or >70, or EMA crossover) is present, rather than defaulting to DOWN. This reduces losing trades on noise.
- **Adaptive Position Sizing Cap**: Lower max exposure from $30 to $15 (15% of capital) to extend runway; this allows the bot to survive longer losing streaks and potentially recover.
- **Dry-Run Mode for Strategy Validation**: Implement `--dry-run` flag that simulates trades without real orders, logging hypothetical P&L. Run this for multiple 90-minute sessions to estimate expected drawdown before risking real capital.

**For Risk 5 (Time Synchronization Drift):**
- **Startup NTP Validation**: Add `validate_time_sync()` function (already in design) that checks NTP offset on startup using `ntplib` library; fail immediately if drift >1s.
- **Interval Drift Correction**: After each interval, calculate actual elapsed time vs. expected 5 minutes and adjust next interval start time to prevent cumulative drift.
- **High-Resolution Timers**: Use `time.perf_counter()` instead of `time.time()` for interval scheduling to avoid leap-second and system clock adjustment issues.

**For Risk 6 (State Corruption on Crash During Settlement):**
- **Two-Phase State Commit**: Save state twice per interval: once immediately after settlement detection (with trade marked "pending") and again after equity update (trade marked "completed"). On recovery, detect pending trades and recheck settlement.
- **State Versioning**: Add version number to `bot_state.json` schema and migration logic to handle corrupted states from older versions.
- **Auto-Recovery Script**: Create `scripts/recover_state.py` that analyzes logs and reconstructs state from `predictions.jsonl` and `trades.jsonl` if `bot_state.json` is corrupted.

**For Risk 7 (Dependency on External Libraries):**
- **Input Validation for Indicators**: Before passing price series to `pandas-ta`, check for edge cases: all prices identical, NaN values, insufficient data points. Return default prediction if detected.
- **Pin Exact Dependency Versions**: In `requirements.txt`, use exact versions (e.g., `pandas-ta==0.3.14b0`) rather than version ranges to prevent breaking changes from library updates.
- **Fallback to NumPy Implementation**: Implement simple RSI and EMA calculation functions using raw NumPy as fallback if `pandas-ta` raises exceptions; log warning and continue with fallback values.

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

### HLD
[Same as input - omitted for brevity]

### LLD
[Same as input - omitted for brevity]