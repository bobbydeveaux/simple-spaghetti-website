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