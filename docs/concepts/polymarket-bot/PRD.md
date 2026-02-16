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