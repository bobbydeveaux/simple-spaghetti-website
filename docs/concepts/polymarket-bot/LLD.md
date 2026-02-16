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