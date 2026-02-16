# Low-Level Design: f4aae091-e557-4fad-93ef-0c81a2a395e1

**Created:** 2026-02-16T15:25:20Z
**Status:** Draft

## 1. Implementation Overview

The Polymarket Bot is implemented as a standalone Python application in a new `polymarket-bot/` directory at the repository root. The implementation uses a single-threaded event loop architecture with async I/O for non-blocking API calls and logging. Core modules include:

- **MarketConnector**: Handles Polymarket API interactions using `requests` library with retry decorators
- **PriceDataProvider**: Manages Binance WebSocket connection using `websockets` library with automatic reconnection
- **PredictionEngine**: Computes RSI and EMA indicators using `pandas-ta` library on rolling price buffer
- **CapitalAllocator**: Implements win-streak scaling logic with `Decimal` precision for currency calculations
- **RiskManager**: Monitors drawdown and volatility thresholds with emergency stop mechanism
- **StateManager**: Persists bot state to JSON using atomic file operations
- **Orchestrator**: Coordinates all components in timed execution loop with drift correction

The bot runs as a CLI application started via `python main.py`, with configuration loaded from `.env` file. All components use synchronous interfaces with async methods wrapped in `asyncio.run()` for I/O operations. State persistence occurs after each trade settlement to enable crash recovery.

---

## 2. File Structure

```
polymarket-bot/
├── .env.example                    # Template for environment variables
├── .gitignore                      # Exclude .env, data/, __pycache__
├── README.md                       # Setup and usage instructions
├── requirements.txt                # Python dependencies with pinned versions
├── main.py                         # Application entry point and orchestrator
├── config.py                       # Configuration loader and validation
├── data/                           # State and log storage (gitignored)
│   ├── bot_state.json              # Persistent bot state
│   ├── predictions.jsonl           # Prediction log entries
│   ├── trades.jsonl                # Trade outcome log entries
│   └── equity_curve.csv            # Final equity export
├── core/
│   ├── __init__.py
│   ├── market_connector.py         # Polymarket API client
│   ├── price_provider.py           # BTC price feed manager
│   ├── prediction_engine.py        # RSI/EMA calculation and signal logic
│   ├── capital_allocator.py        # Position sizing with win-streak scaling
│   ├── risk_manager.py             # Drawdown and volatility checks
│   ├── state_manager.py            # JSON state persistence
│   └── logger.py                   # Async JSONL logging
├── models/
│   ├── __init__.py
│   ├── bot_state.py                # BotState dataclass
│   ├── position.py                 # Position dataclass
│   ├── prediction.py               # Prediction dataclass
│   └── trade_outcome.py            # TradeOutcome dataclass
├── utils/
│   ├── __init__.py
│   ├── retry.py                    # Exponential backoff retry decorator
│   ├── time_sync.py                # NTP drift validation
│   └── validation.py               # Price anomaly detection
├── tests/
│   ├── __init__.py
│   ├── test_market_connector.py    # Mock API tests
│   ├── test_price_provider.py      # Price buffer tests
│   ├── test_prediction_engine.py   # Indicator calculation tests
│   ├── test_capital_allocator.py   # Position sizing tests
│   ├── test_risk_manager.py        # Risk threshold tests
│   ├── test_state_manager.py       # State persistence tests
│   └── test_integration.py         # End-to-end simulation
├── scripts/
│   ├── setup.sh                    # Environment setup script
│   └── deploy_systemd.sh           # systemd service installation
└── Dockerfile                      # Optional containerization
```

**New Files:** All files in `polymarket-bot/` directory (entire application is new)

**Modified Files:** None (standalone application)

---

## 3. Detailed Component Designs

### 3.1 MarketConnector (`core/market_connector.py`)

**Responsibilities:**
- Authenticate with Polymarket API
- Fetch market metadata and odds
- Submit market orders
- Poll settlement status

**Key Classes:**
```python
class MarketConnector:
    def __init__(self, api_key: str, base_url: str = "https://api.polymarket.com"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {api_key}"})
    
    @retry(max_attempts=3, backoff_factor=2)
    def get_market_data(self, timestamp: datetime) -> Dict[str, Any]:
        """Fetch current BTC 5-minute market metadata and odds."""
        market_id = self._generate_market_id(timestamp)
        response = self.session.get(f"{self.base_url}/markets/{market_id}")
        response.raise_for_status()
        return response.json()
    
    @retry(max_attempts=3, backoff_factor=2)
    def submit_order(self, market_id: str, outcome: str, amount: Decimal) -> Dict[str, Any]:
        """Submit market order and return order details."""
        payload = {
            "market_id": market_id,
            "outcome": outcome,
            "amount": float(amount),
            "type": "market"
        }
        response = self.session.post(f"{self.base_url}/orders", json=payload)
        response.raise_for_status()
        return response.json()
    
    def poll_settlement(self, market_id: str, timeout_seconds: int = 300) -> Optional[str]:
        """Poll market resolution every 15s until settled or timeout."""
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            response = self.session.get(f"{self.base_url}/markets/{market_id}/resolution")
            if response.status_code == 200:
                data = response.json()
                if data.get("resolved"):
                    return data["winning_outcome"]
            time.sleep(15)
        raise TimeoutError(f"Market {market_id} did not settle within {timeout_seconds}s")
    
    def _generate_market_id(self, timestamp: datetime) -> str:
        """Generate market ID from timestamp (format: btc-5min-YYYYMMDD-HHMM)."""
        return f"btc-5min-{timestamp.strftime('%Y%m%d-%H%M')}"
```

**Error Handling:**
- Retry on HTTP 429, 500, 502, 503 (transient errors)
- Raise on 401/403 (auth errors, should halt bot)
- Log all API errors with response body

---

### 3.2 PriceDataProvider (`core/price_provider.py`)

**Responsibilities:**
- Establish and maintain Binance WebSocket connection
- Populate rolling price buffer (60 data points, 30-minute window)
- Fallback to Coinbase/CoinGecko REST APIs
- Validate price data integrity

**Key Classes:**
```python
from collections import deque
from websockets.sync.client import connect

class PriceDataProvider:
    def __init__(self, buffer_size: int = 60):
        self.prices: Deque[PricePoint] = deque(maxlen=buffer_size)
        self.ws_url = "wss://stream.binance.com:9443/ws/btcusdt@ticker"
        self.ws_connection = None
        self.last_price = None
        self.baseline_volatility = None
    
    def start(self):
        """Establish WebSocket connection and start price collection."""
        self._connect_websocket()
        self._populate_initial_buffer()
    
    def _connect_websocket(self):
        """Connect to Binance WebSocket with reconnection logic."""
        try:
            self.ws_connection = connect(self.ws_url)
        except Exception as e:
            logger.warning(f"Binance WebSocket failed: {e}, falling back to REST")
            self.ws_connection = None
    
    def _populate_initial_buffer(self):
        """Collect initial 60 prices over 30 minutes (30s intervals)."""
        for _ in range(60):
            price_point = self._fetch_price()
            if price_point:
                self.prices.append(price_point)
                self.last_price = price_point.price
            time.sleep(30)
        self.baseline_volatility = self.calculate_volatility()
    
    def _fetch_price(self) -> Optional[PricePoint]:
        """Fetch single price from WebSocket or REST fallback."""
        if self.ws_connection:
            try:
                message = self.ws_connection.recv(timeout=5)
                data = json.loads(message)
                price = float(data["c"])
                if self._validate_price(price):
                    return PricePoint(
                        timestamp=datetime.now(),
                        price=price,
                        source="binance"
                    )
            except Exception as e:
                logger.warning(f"WebSocket recv failed: {e}, reconnecting")
                self._connect_websocket()
        
        # Fallback to REST APIs
        return self._fetch_rest_price()
    
    def _fetch_rest_price(self) -> Optional[PricePoint]:
        """Fetch price from Coinbase, then CoinGecko if failed."""
        try:
            response = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=5)
            price = float(response.json()["data"]["amount"])
            if self._validate_price(price):
                return PricePoint(timestamp=datetime.now(), price=price, source="coinbase")
        except Exception as e:
            logger.warning(f"Coinbase failed: {e}, trying CoinGecko")
        
        try:
            response = requests.get(
                "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
                timeout=5
            )
            price = float(response.json()["bitcoin"]["usd"])
            if self._validate_price(price):
                return PricePoint(timestamp=datetime.now(), price=price, source="coingecko")
        except Exception as e:
            logger.error(f"All price feeds failed: {e}")
            return None
    
    def _validate_price(self, price: float) -> bool:
        """Reject price if >10% deviation from last known price."""
        if self.last_price is None:
            return True
        deviation = abs(price - self.last_price) / self.last_price
        if deviation > 0.10:
            logger.warning(f"Price anomaly detected: {price} vs {self.last_price}")
            return False
        return True
    
    def calculate_volatility(self) -> float:
        """Calculate standard deviation of last 10 prices."""
        if len(self.prices) < 10:
            return 0.0
        recent_prices = [p.price for p in list(self.prices)[-10:]]
        return float(np.std(recent_prices))
    
    def get_price_series(self) -> pd.Series:
        """Return price buffer as pandas Series for indicator calculation."""
        return pd.Series([p.price for p in self.prices])
```

**PricePoint Dataclass:**
```python
@dataclass
class PricePoint:
    timestamp: datetime
    price: float
    source: str  # "binance" | "coinbase" | "coingecko"
```

---

### 3.3 PredictionEngine (`core/prediction_engine.py`)

**Responsibilities:**
- Calculate 14-period RSI using Wilder's smoothing
- Calculate 9-period and 21-period EMA
- Apply deterministic signal rules
- Output prediction with confidence metadata

**Key Classes:**
```python
import pandas_ta as ta

class PredictionEngine:
    def __init__(self, rsi_period: int = 14, ema_short: int = 9, ema_long: int = 21):
        self.rsi_period = rsi_period
        self.ema_short = ema_short
        self.ema_long = ema_long
        self.prev_ema_short = None
        self.prev_ema_long = None
    
    def predict(self, price_series: pd.Series) -> Prediction:
        """Generate UP/DOWN prediction based on RSI and EMA crossover."""
        if len(price_series) < max(self.rsi_period, self.ema_long):
            return self._default_prediction(price_series)
        
        # Calculate indicators
        rsi = ta.rsi(price_series, length=self.rsi_period).iloc[-1]
        ema_short = ta.ema(price_series, length=self.ema_short).iloc[-1]
        ema_long = ta.ema(price_series, length=self.ema_long).iloc[-1]
        
        # Determine signal
        signal_type, prediction, confidence = self._apply_signal_rules(
            rsi, ema_short, ema_long
        )
        
        # Update previous EMA values for crossover detection
        self.prev_ema_short = ema_short
        self.prev_ema_long = ema_long
        
        return Prediction(
            timestamp=datetime.now(),
            btc_price=price_series.iloc[-1],
            rsi_14=rsi,
            ema_9=ema_short,
            ema_21=ema_long,
            signal_type=signal_type,
            prediction=prediction,
            confidence=confidence
        )
    
    def _apply_signal_rules(
        self, rsi: float, ema_short: float, ema_long: float
    ) -> Tuple[str, str, str]:
        """Apply deterministic signal rules and return (signal_type, prediction, confidence)."""
        # RSI oversold (high confidence UP)
        if rsi < 30:
            return ("RSI_OVERSOLD", "UP", "high")
        
        # RSI overbought (high confidence DOWN)
        if rsi > 70:
            return ("RSI_OVERBOUGHT", "DOWN", "high")
        
        # EMA crossover (medium confidence)
        if self.prev_ema_short is not None and self.prev_ema_long is not None:
            # Bullish crossover: 9-EMA crosses above 21-EMA
            if ema_short > ema_long and self.prev_ema_short <= self.prev_ema_long:
                return ("EMA_BULLISH_CROSSOVER", "UP", "medium")
            
            # Bearish crossover: 9-EMA crosses below 21-EMA
            if ema_short < ema_long and self.prev_ema_short >= self.prev_ema_long:
                return ("EMA_BEARISH_CROSSOVER", "DOWN", "medium")
        
        # No signal: default to DOWN (conservative bias)
        return ("NO_SIGNAL", "DOWN", "low")
    
    def _default_prediction(self, price_series: pd.Series) -> Prediction:
        """Return default DOWN prediction when insufficient data."""
        return Prediction(
            timestamp=datetime.now(),
            btc_price=price_series.iloc[-1] if len(price_series) > 0 else 0.0,
            rsi_14=None,
            ema_9=None,
            ema_21=None,
            signal_type="INSUFFICIENT_DATA",
            prediction="DOWN",
            confidence="low"
        )
```

---

### 3.4 CapitalAllocator (`core/capital_allocator.py`)

**Responsibilities:**
- Track current equity and win streak
- Calculate position size with win-streak scaling
- Validate position size against available equity

**Key Classes:**
```python
from decimal import Decimal, ROUND_DOWN

class CapitalAllocator:
    def __init__(
        self,
        starting_capital: Decimal,
        base_size: Decimal = Decimal("5.00"),
        multiplier: Decimal = Decimal("1.5"),
        max_exposure: Decimal = Decimal("30.00")
    ):
        self.starting_capital = starting_capital
        self.current_equity = starting_capital
        self.base_size = base_size
        self.multiplier = multiplier
        self.max_exposure = max_exposure
        self.win_streak = 0
        self.trade_count = 0
    
    def calculate_position_size(self) -> Decimal:
        """Calculate position size based on win streak, capped at max exposure."""
        if self.win_streak == 0:
            position_size = self.base_size
        else:
            position_size = self.base_size * (self.multiplier ** self.win_streak)
        
        # Cap at max exposure
        position_size = min(position_size, self.max_exposure)
        
        # Cap at available equity
        position_size = min(position_size, self.current_equity)
        
        # Round down to 2 decimal places
        return position_size.quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    
    def validate_position_size(self, position_size: Decimal) -> bool:
        """Validate position size is within acceptable bounds."""
        if position_size <= Decimal("0"):
            logger.error("Position size must be positive")
            return False
        
        if position_size > self.current_equity:
            logger.error(f"Position size {position_size} exceeds equity {self.current_equity}")
            return False
        
        if position_size > self.max_exposure:
            logger.error(f"Position size {position_size} exceeds max exposure {self.max_exposure}")
            return False
        
        return True
    
    def update_after_trade(self, pnl: Decimal, is_win: bool):
        """Update equity and win streak after trade settlement."""
        self.current_equity += pnl
        self.trade_count += 1
        
        if is_win:
            self.win_streak += 1
        else:
            self.win_streak = 0
        
        logger.info(f"Equity: {self.current_equity}, Win Streak: {self.win_streak}")
```

---

### 3.5 RiskManager (`core/risk_manager.py`)

**Responsibilities:**
- Monitor drawdown percentage
- Check volatility filter
- Trigger emergency stop

**Key Classes:**
```python
class RiskManager:
    def __init__(
        self,
        starting_capital: Decimal,
        max_drawdown_pct: Decimal = Decimal("0.30"),
        volatility_multiplier: float = 2.0
    ):
        self.starting_capital = starting_capital
        self.max_drawdown_pct = max_drawdown_pct
        self.volatility_multiplier = volatility_multiplier
        self.emergency_stop = False
    
    def check_drawdown(self, current_equity: Decimal) -> bool:
        """Check if drawdown exceeds threshold, trigger emergency stop if needed."""
        drawdown = (self.starting_capital - current_equity) / self.starting_capital
        
        if drawdown >= self.max_drawdown_pct:
            logger.critical(
                f"Emergency stop triggered: drawdown {drawdown:.2%} >= {self.max_drawdown_pct:.2%}"
            )
            self.emergency_stop = True
            return False
        
        return True
    
    def check_volatility(self, current_volatility: float, baseline_volatility: float) -> bool:
        """Check if current volatility exceeds safe threshold."""
        if baseline_volatility == 0:
            return True
        
        if current_volatility > baseline_volatility * self.volatility_multiplier:
            logger.warning(
                f"Volatility filter triggered: {current_volatility:.4f} > "
                f"{baseline_volatility * self.volatility_multiplier:.4f}"
            )
            return False
        
        return True
    
    def is_emergency_stop(self) -> bool:
        """Check if emergency stop has been triggered."""
        return self.emergency_stop
```

---

### 3.6 StateManager (`core/state_manager.py`)

**Responsibilities:**
- Load bot state from JSON on startup
- Save bot state after each trade settlement
- Atomic file operations to prevent corruption

**Key Classes:**
```python
import json
import os
from pathlib import Path

class StateManager:
    def __init__(self, state_file: Path = Path("data/bot_state.json")):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
    
    def load_state(self) -> Optional[BotState]:
        """Load bot state from JSON file, return None if not exists."""
        if not self.state_file.exists():
            return None
        
        try:
            with open(self.state_file, "r") as f:
                data = json.load(f)
                return BotState.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load state: {e}")
            return None
    
    def save_state(self, state: BotState):
        """Save bot state to JSON file with atomic write-replace."""
        temp_file = self.state_file.with_suffix(".tmp")
        
        try:
            with open(temp_file, "w") as f:
                json.dump(state.to_dict(), f, indent=2, default=str)
            
            # Atomic rename (crash-safe)
            os.replace(temp_file, self.state_file)
            logger.debug(f"State saved to {self.state_file}")
        
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
            if temp_file.exists():
                temp_file.unlink()
    
    def export_equity_curve(self, equity_curve: List[Dict[str, Any]]):
        """Export equity curve to CSV."""
        csv_file = self.state_file.parent / "equity_curve.csv"
        
        try:
            df = pd.DataFrame(equity_curve)
            df.to_csv(csv_file, index=False)
            logger.info(f"Equity curve exported to {csv_file}")
        except Exception as e:
            logger.error(f"Failed to export equity curve: {e}")
```

---

### 3.7 Logger (`core/logger.py`)

**Responsibilities:**
- Async JSONL logging for predictions and trades
- Console output for real-time monitoring
- Log flushing on shutdown

**Key Classes:**
```python
import asyncio
import logging
from pathlib import Path

class BotLogger:
    def __init__(self, log_dir: Path = Path("data")):
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.prediction_file = log_dir / "predictions.jsonl"
        self.trade_file = log_dir / "trades.jsonl"
        
        # Setup console logger
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(),
                logging.FileHandler(log_dir / "bot.log")
            ]
        )
        self.logger = logging.getLogger("polymarket_bot")
    
    async def log_prediction(self, prediction: Prediction):
        """Log prediction to JSONL file."""
        await self._append_jsonl(self.prediction_file, prediction.to_dict())
        self.logger.info(
            f"Prediction: {prediction.prediction} | "
            f"RSI: {prediction.rsi_14:.2f} | "
            f"Signal: {prediction.signal_type}"
        )
    
    async def log_trade(self, trade_outcome: TradeOutcome):
        """Log trade outcome to JSONL file."""
        await self._append_jsonl(self.trade_file, trade_outcome.to_dict())
        self.logger.info(
            f"Trade: {'WIN' if trade_outcome.win else 'LOSS'} | "
            f"P&L: {trade_outcome.pnl:+.2f} | "
            f"Equity: {trade_outcome.equity_after:.2f} | "
            f"Streak: {trade_outcome.win_streak}"
        )
    
    async def _append_jsonl(self, file: Path, data: dict):
        """Append JSON line to file asynchronously."""
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._write_line,
                file,
                json.dumps(data, default=str)
            )
        except Exception as e:
            self.logger.error(f"Failed to write log: {e}")
    
    def _write_line(self, file: Path, line: str):
        """Synchronous write helper."""
        with open(file, "a") as f:
            f.write(line + "\n")
```

---

### 3.8 Orchestrator (`main.py`)

**Responsibilities:**
- Initialize all components
- Execute 18-interval trading loop
- Handle graceful shutdown

**Key Functions:**
```python
import signal
import sys
from datetime import datetime, timedelta

def main():
    """Main entry point for Polymarket Bot."""
    # Load configuration
    config = Config.from_env()
    
    # Validate time sync
    validate_time_sync()
    
    # Initialize components
    market_connector = MarketConnector(config.api_key)
    price_provider = PriceDataProvider()
    prediction_engine = PredictionEngine()
    capital_allocator = CapitalAllocator(Decimal(config.starting_capital))
    risk_manager = RiskManager(Decimal(config.starting_capital))
    state_manager = StateManager()
    bot_logger = BotLogger()
    
    # Load state if exists
    saved_state = state_manager.load_state()
    if saved_state:
        capital_allocator.current_equity = saved_state.current_equity
        capital_allocator.win_streak = saved_state.win_streak
        capital_allocator.trade_count = saved_state.trade_count
        logger.info(f"Resumed from saved state: equity={saved_state.current_equity}")
    
    # Setup graceful shutdown
    def shutdown_handler(signum, frame):
        logger.info("Shutdown signal received, saving state...")
        state_manager.save_state(build_bot_state(capital_allocator, risk_manager))
        state_manager.export_equity_curve(equity_curve)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    
    # Start price provider
    logger.info("Starting price feed...")
    price_provider.start()
    
    # Main execution loop (18 intervals)
    equity_curve = []
    start_time = datetime.now()
    
    for interval in range(18):
        interval_start = start_time + timedelta(minutes=5 * interval)
        logger.info(f"=== Interval {interval + 1}/18 at {interval_start} ===")
        
        # Wait until interval start
        wait_until(interval_start)
        
        # Check emergency stop
        if risk_manager.is_emergency_stop():
            logger.critical("Emergency stop active, halting trading")
            break
        
        # Fetch latest price
        price_provider._fetch_price()
        
        # Check volatility filter
        current_volatility = price_provider.calculate_volatility()
        if not risk_manager.check_volatility(current_volatility, price_provider.baseline_volatility):
            logger.warning("Skipping interval due to high volatility")
            continue
        
        # Generate prediction
        price_series = price_provider.get_price_series()
        prediction = prediction_engine.predict(price_series)
        asyncio.run(bot_logger.log_prediction(prediction))
        
        # Calculate position size
        position_size = capital_allocator.calculate_position_size()
        if not capital_allocator.validate_position_size(position_size):
            logger.error("Invalid position size, skipping interval")
            continue
        
        # Fetch market data
        try:
            market_data = market_connector.get_market_data(interval_start)
            market_id = market_data["market_id"]
            market_odds = market_data["odds"]
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}, skipping interval")
            continue
        
        # Submit order
        try:
            order_response = market_connector.submit_order(
                market_id, prediction.prediction, position_size
            )
            logger.info(f"Order placed: {order_response}")
        except Exception as e:
            logger.error(f"Failed to submit order: {e}, skipping interval")
            continue
        
        # Poll settlement
        try:
            winning_outcome = market_connector.poll_settlement(market_id, timeout_seconds=300)
        except TimeoutError as e:
            logger.error(f"Settlement timeout: {e}")
            continue
        
        # Calculate P&L
        is_win = (winning_outcome == prediction.prediction)
        if is_win:
            payout_multiplier = 1 / market_odds[prediction.prediction]
            pnl = position_size * Decimal(str(payout_multiplier - 1))
        else:
            pnl = -position_size
        
        # Update capital allocator
        equity_before = capital_allocator.current_equity
        capital_allocator.update_after_trade(pnl, is_win)
        
        # Log trade outcome
        trade_outcome = TradeOutcome(
            settlement_time=datetime.now(),
            prediction=prediction.prediction,
            actual_direction=winning_outcome,
            win=is_win,
            pnl=pnl,
            position_size=position_size,
            equity_before=equity_before,
            equity_after=capital_allocator.current_equity,
            win_streak=capital_allocator.win_streak,
            market_odds=market_odds
        )
        asyncio.run(bot_logger.log_trade(trade_outcome))
        
        # Update equity curve
        equity_curve.append({
            "timestamp": datetime.now(),
            "equity": float(capital_allocator.current_equity)
        })
        
        # Save state
        state_manager.save_state(build_bot_state(capital_allocator, risk_manager))
        
        # Check drawdown
        if not risk_manager.check_drawdown(capital_allocator.current_equity):
            break
    
    # Final export
    state_manager.export_equity_curve(equity_curve)
    logger.info(f"Bot completed. Final equity: {capital_allocator.current_equity}")

def wait_until(target_time: datetime):
    """Sleep until target time with drift correction."""
    while datetime.now() < target_time:
        time.sleep(0.1)

def build_bot_state(allocator: CapitalAllocator, risk_mgr: RiskManager) -> BotState:
    """Build BotState object from current allocator state."""
    return BotState(
        starting_capital=allocator.starting_capital,
        current_equity=allocator.current_equity,
        win_streak=allocator.win_streak,
        trade_count=allocator.trade_count,
        emergency_stop=risk_mgr.emergency_stop
    )

if __name__ == "__main__":
    main()
```

---

## 4. Database Schema Changes

**N/A** - This application does not use a database. All state is persisted to JSON files and logs to JSONL files.

---

## 5. API Implementation Details

### 5.1 Polymarket API Client

**Base URL:** `https://api.polymarket.com` (assumed)

**Authentication:**
- Header: `Authorization: Bearer {api_key}`
- API key loaded from `POLYMARKET_API_KEY` environment variable

**Endpoints:**

**GET /markets/{market_id}**
- **Handler:** `MarketConnector.get_market_data()`
- **Retry Logic:** 3 attempts with exponential backoff (1s, 2s, 4s)
- **Validation:** Check response contains `market_id`, `outcomes`, `odds`, `settlement_time`
- **Error Handling:**
  - 401/403: Log critical error and raise (should halt bot)
  - 429: Retry with backoff
  - 500/502/503: Retry with backoff
  - Timeout: Log warning and skip interval

**POST /orders**
- **Handler:** `MarketConnector.submit_order()`
- **Payload Validation:** Ensure `amount > 0`, `outcome in ["UP", "DOWN"]`, `market_id` is valid
- **Response Validation:** Check `status == "filled"`, extract `order_id`
- **Error Handling:**
  - 400: Log validation error, skip interval
  - 429: Retry with backoff
  - 500/502/503: Retry with backoff
  - Insufficient funds: Log critical error, trigger emergency stop

**GET /markets/{market_id}/resolution**
- **Handler:** `MarketConnector.poll_settlement()`
- **Polling Strategy:** Poll every 15 seconds for up to 5 minutes (300s timeout)
- **Success Condition:** `resolved == true` in response
- **Return:** `winning_outcome` field
- **Error Handling:**
  - Timeout: Log error, mark interval as incomplete, continue to next
  - Invalid response: Log error and retry

---

### 5.2 External Price APIs

**Binance WebSocket**
- **URL:** `wss://stream.binance.com:9443/ws/btcusdt@ticker`
- **Handler:** `PriceDataProvider._connect_websocket()`
- **Message Format:** Extract `data["c"]` (current price) and `data["E"]` (event time)
- **Reconnection:** On disconnect, wait 5s and reconnect (max 3 attempts)

**Coinbase REST**
- **URL:** `https://api.coinbase.com/v2/prices/BTC-USD/spot`
- **Handler:** `PriceDataProvider._fetch_rest_price()`
- **Extraction:** `response.json()["data"]["amount"]`
- **Timeout:** 5 seconds

**CoinGecko REST**
- **URL:** `https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd`
- **Handler:** `PriceDataProvider._fetch_rest_price()`
- **Extraction:** `response.json()["bitcoin"]["usd"]`
- **Timeout:** 5 seconds

---

## 6. Function Signatures

### Core Modules

**MarketConnector**
```python
def __init__(self, api_key: str, base_url: str = "https://api.polymarket.com")
def get_market_data(self, timestamp: datetime) -> Dict[str, Any]
def submit_order(self, market_id: str, outcome: str, amount: Decimal) -> Dict[str, Any]
def poll_settlement(self, market_id: str, timeout_seconds: int = 300) -> Optional[str]
def _generate_market_id(self, timestamp: datetime) -> str
```

**PriceDataProvider**
```python
def __init__(self, buffer_size: int = 60)
def start(self) -> None
def _connect_websocket(self) -> None
def _populate_initial_buffer(self) -> None
def _fetch_price(self) -> Optional[PricePoint]
def _fetch_rest_price(self) -> Optional[PricePoint]
def _validate_price(self, price: float) -> bool
def calculate_volatility(self) -> float
def get_price_series(self) -> pd.Series
```

**PredictionEngine**
```python
def __init__(self, rsi_period: int = 14, ema_short: int = 9, ema_long: int = 21)
def predict(self, price_series: pd.Series) -> Prediction
def _apply_signal_rules(self, rsi: float, ema_short: float, ema_long: float) -> Tuple[str, str, str]
def _default_prediction(self, price_series: pd.Series) -> Prediction
```

**CapitalAllocator**
```python
def __init__(self, starting_capital: Decimal, base_size: Decimal = Decimal("5.00"), multiplier: Decimal = Decimal("1.5"), max_exposure: Decimal = Decimal("30.00"))
def calculate_position_size(self) -> Decimal
def validate_position_size(self, position_size: Decimal) -> bool
def update_after_trade(self, pnl: Decimal, is_win: bool) -> None
```

**RiskManager**
```python
def __init__(self, starting_capital: Decimal, max_drawdown_pct: Decimal = Decimal("0.30"), volatility_multiplier: float = 2.0)
def check_drawdown(self, current_equity: Decimal) -> bool
def check_volatility(self, current_volatility: float, baseline_volatility: float) -> bool
def is_emergency_stop(self) -> bool
```

**StateManager**
```python
def __init__(self, state_file: Path = Path("data/bot_state.json"))
def load_state(self) -> Optional[BotState]
def save_state(self, state: BotState) -> None
def export_equity_curve(self, equity_curve: List[Dict[str, Any]]) -> None
```

**BotLogger**
```python
def __init__(self, log_dir: Path = Path("data"))
async def log_prediction(self, prediction: Prediction) -> None
async def log_trade(self, trade_outcome: TradeOutcome) -> None
async def _append_jsonl(self, file: Path, data: dict) -> None
def _write_line(self, file: Path, line: str) -> None
```

### Utility Functions

**utils/retry.py**
```python
def retry(max_attempts: int = 3, backoff_factor: float = 2.0, exceptions: Tuple = (Exception,)) -> Callable
```

**utils/time_sync.py**
```python
def validate_time_sync(max_drift_ms: int = 1000) -> bool
def get_ntp_offset() -> float
```

**utils/validation.py**
```python
def validate_price_anomaly(price: float, last_price: float, max_deviation: float = 0.10) -> bool
def validate_market_data(data: Dict[str, Any]) -> bool
```

---

## 7. State Management

**State Persistence:**
- Bot state stored in `data/bot_state.json` as JSON
- State saved after each trade settlement using atomic write-replace pattern
- State loaded on startup to enable crash recovery

**BotState Structure:**
```python
@dataclass
class BotState:
    starting_capital: Decimal
    current_equity: Decimal
    win_streak: int
    trade_count: int
    last_position: Optional[Dict[str, Any]]
    equity_curve: List[Dict[str, Any]]
    baseline_volatility: float
    emergency_stop: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "starting_capital": float(self.starting_capital),
            "current_equity": float(self.current_equity),
            "win_streak": self.win_streak,
            "trade_count": self.trade_count,
            "last_position": self.last_position,
            "equity_curve": self.equity_curve,
            "baseline_volatility": self.baseline_volatility,
            "emergency_stop": self.emergency_stop
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BotState":
        return cls(
            starting_capital=Decimal(str(data["starting_capital"])),
            current_equity=Decimal(str(data["current_equity"])),
            win_streak=data["win_streak"],
            trade_count=data["trade_count"],
            last_position=data.get("last_position"),
            equity_curve=data.get("equity_curve", []),
            baseline_volatility=data.get("baseline_volatility", 0.0),
            emergency_stop=data.get("emergency_stop", False)
        )
```

**In-Memory State:**
- `PriceDataProvider.prices`: Rolling deque of last 60 prices
- `CapitalAllocator`: Current equity, win streak, trade count
- `RiskManager`: Emergency stop flag
- `PredictionEngine`: Previous EMA values for crossover detection

**State Recovery:**
- On startup, check if `bot_state.json` exists
- If exists, load equity, win streak, trade count, and resume from last position
- If not exists, start fresh with initial capital

---

## 8. Error Handling Strategy

**Error Categories:**

**1. API Errors (Transient)**
- **Codes:** 429 (rate limit), 500, 502, 503 (server errors)
- **Handling:** Exponential backoff retry (max 3 attempts)
- **Fallback:** Skip interval if all retries fail

**2. Authentication Errors (Fatal)**
- **Codes:** 401 (unauthorized), 403 (forbidden)
- **Handling:** Log critical error, trigger emergency stop, halt bot

**3. Price Feed Errors (Recoverable)**
- **Scenarios:** WebSocket disconnect, REST API timeout, price anomaly
- **Handling:** Reconnect WebSocket, fallback to REST APIs (Coinbase → CoinGecko)
- **Fallback:** Skip interval if all feeds fail

**4. Validation Errors (Skip Interval)**
- **Scenarios:** Invalid position size, insufficient equity, invalid market data
- **Handling:** Log error, skip current interval, continue to next

**5. Settlement Timeout (Non-Fatal)**
- **Scenario:** Market does not settle within 5 minutes
- **Handling:** Log error, skip outcome logging, continue to next interval

**Error Codes:**
```python
class ErrorCode(Enum):
    API_AUTH_FAILED = "E001"
    API_RATE_LIMITED = "E002"
    API_SERVER_ERROR = "E003"
    PRICE_FEED_FAILED = "E004"
    PRICE_ANOMALY = "E005"
    POSITION_VALIDATION_FAILED = "E006"
    SETTLEMENT_TIMEOUT = "E007"
    EMERGENCY_STOP_TRIGGERED = "E008"
```

**Exception Hierarchy:**
```python
class BotException(Exception):
    """Base exception for bot errors."""
    def __init__(self, code: ErrorCode, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code.value}] {message}")

class APIException(BotException):
    """API-related errors."""
    pass

class PriceFeedException(BotException):
    """Price feed errors."""
    pass

class RiskException(BotException):
    """Risk management errors."""
    pass
```

**User-Facing Messages:**
- All errors logged to `data/bot.log` with timestamps
- Console output shows simplified messages (e.g., "Skipping interval due to high volatility")
- Critical errors (auth failures, emergency stop) display prominent warnings

---

## 9. Test Plan

### Unit Tests

**test_market_connector.py**
```python
def test_get_market_data_success():
    """Test successful market data fetch."""
    # Mock API response, assert correct parsing

def test_get_market_data_retry_on_429():
    """Test retry logic on rate limit."""
    # Mock 429 response, assert exponential backoff

def test_submit_order_validation():
    """Test order payload validation."""
    # Test invalid amounts, outcomes, market IDs

def test_poll_settlement_timeout():
    """Test settlement polling timeout."""
    # Mock unresolved market, assert TimeoutError after 300s
```

**test_price_provider.py**
```python
def test_fetch_price_binance():
    """Test WebSocket price fetch."""
    # Mock WebSocket message, assert PricePoint created

def test_fetch_price_fallback_coinbase():
    """Test fallback to Coinbase on WebSocket failure."""
    # Mock WebSocket failure, assert Coinbase API called

def test_validate_price_anomaly():
    """Test price anomaly detection."""
    # Test >10% deviation rejected

def test_calculate_volatility():
    """Test volatility calculation."""
    # Populate buffer, assert std dev calculation
```

**test_prediction_engine.py**
```python
def test_predict_rsi_oversold():
    """Test RSI < 30 triggers UP prediction."""
    # Mock price series with RSI=25, assert UP

def test_predict_ema_crossover():
    """Test EMA crossover detection."""
    # Mock EMA 9 crossing above EMA 21, assert UP

def test_predict_default_no_signal():
    """Test default DOWN when no signal."""
    # Mock neutral indicators, assert DOWN
```

**test_capital_allocator.py**
```python
def test_calculate_position_size_base():
    """Test base position size with no streak."""
    # Assert position_size = $5.00

def test_calculate_position_size_streak():
    """Test position scaling with win streak."""
    # Win streak=2, assert position_size = 5 * (1.5^2) = $11.25

def test_calculate_position_size_capped():
    """Test position size capped at max exposure."""
    # Win streak=5, assert position_size = $30.00

def test_update_after_trade_win():
    """Test streak increment on win."""
    # Simulate win, assert streak += 1

def test_update_after_trade_loss():
    """Test streak reset on loss."""
    # Simulate loss, assert streak = 0
```

**test_risk_manager.py**
```python
def test_check_drawdown_within_threshold():
    """Test drawdown within safe limits."""
    # Equity at $80, assert passes

def test_check_drawdown_exceeds_threshold():
    """Test emergency stop on 30% drawdown."""
    # Equity at $69, assert emergency_stop = True

def test_check_volatility_normal():
    """Test volatility within normal range."""
    # Volatility 1.5x baseline, assert passes

def test_check_volatility_high():
    """Test volatility filter triggered."""
    # Volatility 2.5x baseline, assert fails
```

**test_state_manager.py**
```python
def test_save_load_state_roundtrip():
    """Test state save and load preserve data."""
    # Save state, load, assert equality

def test_atomic_write_on_crash():
    """Test atomic write prevents corruption."""
    # Simulate crash during write, assert original file intact

def test_export_equity_curve():
    """Test CSV export."""
    # Save equity curve, assert CSV contains correct data
```

### Integration Tests

**test_integration.py**
```python
def test_single_interval_execution():
    """Test complete flow for one trading interval."""
    # Mock all external APIs, run one iteration of main loop
    # Assert prediction logged, order submitted, outcome processed

def test_win_streak_flow():
    """Test multi-interval execution with win streak."""
    # Mock 3 consecutive wins, assert position size scales correctly

def test_emergency_stop_flow():
    """Test bot halts on drawdown threshold."""
    # Mock losing trades to trigger 30% drawdown, assert bot stops

def test_volatility_filter_skip():
    """Test interval skipped on high volatility."""
    # Mock high volatility, assert no trade placed

def test_price_feed_failover():
    """Test fallback to REST APIs on WebSocket failure."""
    # Mock WebSocket disconnect, assert Coinbase called

def test_crash_recovery():
    """Test bot resumes from saved state after crash."""
    # Save state mid-session, restart bot, assert equity/streak restored
```

### E2E Tests

**test_e2e.py**
```python
def test_full_90_minute_session():
    """Test complete 18-interval trading session."""
    # Mock all APIs with realistic responses
    # Run main() to completion
    # Assert 18 trades logged, equity curve exported, state saved

def test_session_with_mixed_outcomes():
    """Test session with wins, losses, and skipped intervals."""
    # Mock varied outcomes (3 wins, 2 losses, 1 skip)
    # Assert final equity matches expected value

def test_session_with_emergency_stop():
    """Test session halts early on emergency stop."""
    # Mock losing streak to trigger drawdown
    # Assert bot stops before 18 intervals
```

**Manual Testing Checklist:**
- [ ] Deploy to test VPS, verify time sync with NTP
- [ ] Run with Polymarket testnet API (if available)
- [ ] Monitor console output for 90 minutes
- [ ] Verify all logs written correctly
- [ ] Test graceful shutdown with Ctrl+C
- [ ] Verify equity curve CSV export
- [ ] Test crash recovery by killing process mid-interval
- [ ] Verify emergency stop triggers at 30% drawdown

---

## 10. Migration Strategy

**This is a new standalone application with no existing codebase to migrate from.**

**Deployment Steps:**

1. **Environment Setup**
   ```bash
   cd polymarket-bot/
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configuration**
   ```bash
   cp .env.example .env
   # Edit .env to add POLYMARKET_API_KEY and other secrets
   chmod 600 .env
   ```

3. **Time Sync Validation**
   ```bash
   timedatectl status
   # Ensure NTP is active and time synchronized
   ```

4. **Test Run (Dry Mode - Optional Enhancement)**
   ```bash
   # Future enhancement: add --dry-run flag to simulate without real trades
   python main.py --dry-run
   ```

5. **Production Run**
   ```bash
   python main.py
   ```

6. **Systemd Service (Optional)**
   ```bash
   sudo ./scripts/deploy_systemd.sh
   sudo systemctl start polymarket-bot
   sudo systemctl status polymarket-bot
   ```

**Data Migration:**
- No existing data to migrate
- Bot starts fresh with $100 capital on first run
- Subsequent runs load state from `bot_state.json` if exists

---

## 11. Rollback Plan

**Scenario 1: Bot Fails to Start**
- **Symptoms:** Import errors, configuration errors, API auth failures
- **Rollback:** Fix configuration in `.env`, restart
- **Data Loss:** None (no state created yet)

**Scenario 2: Bot Crashes Mid-Execution**
- **Symptoms:** Unhandled exception, process killed
- **Rollback:** Fix bug in code, restart bot
- **Data Loss:** None if state saved before crash; bot resumes from last settlement
- **Recovery:** Load `bot_state.json`, verify equity and streak, continue

**Scenario 3: Emergency Stop Triggered**
- **Symptoms:** Drawdown exceeds 30%, bot halts
- **Rollback:** Not applicable (risk management working as designed)
- **Action:** Review logs, analyze losing streak, adjust strategy parameters if needed
- **Manual Intervention:** Reset state file to resume trading (not recommended without strategy review)

**Scenario 4: API Outage**
- **Symptoms:** All API calls fail, intervals skipped
- **Rollback:** Wait for API to recover, bot will continue to next interval
- **Data Loss:** Missed trading opportunities for skipped intervals
- **Recovery:** No action needed, bot continues when API available

**Rollback Commands:**
```bash
# Stop bot
sudo systemctl stop polymarket-bot

# View logs
tail -n 100 data/bot.log
tail -n 50 data/trades.jsonl | jq .

# Reset state (CAUTION: loses current equity/streak)
mv data/bot_state.json data/bot_state.json.backup

# Restart bot
sudo systemctl start polymarket-bot
```

**Backup Strategy:**
- Logs and state files in `data/` directory backed up after each run
- Optional: Upload `data/` to S3 or GCS after session completion

---

## 12. Performance Considerations

**Latency Optimization:**
- **WebSocket vs REST:** Use Binance WebSocket for price feed to minimize latency (<50ms vs 200-500ms for REST)
- **Async I/O:** Log writes use `asyncio` to prevent blocking execution loop
- **Connection Pooling:** `requests.Session()` reuses HTTP connections for Polymarket API calls

**Memory Optimization:**
- **Fixed-Size Buffer:** `deque(maxlen=60)` for price data prevents unbounded memory growth
- **State Size:** Bot state <1KB, trade logs <100KB for 18 trades (negligible)
- **No Caching:** Indicator values computed on-demand (trade-off: CPU for memory)

**CPU Optimization:**
- **Single-Threaded:** No thread synchronization overhead
- **Indicator Calculation:** RSI/EMA computed in <10ms using `pandas-ta` (optimized C extensions)
- **Idle Waiting:** `time.sleep()` during interval gaps reduces CPU to near-zero

**Network Optimization:**
- **Retry Strategy:** Exponential backoff prevents API hammering on failures
- **Timeout Configuration:** 5s timeout on REST calls prevents hanging
- **WebSocket Reconnection:** 5s backoff on disconnect (not immediate retry)

**Disk I/O Optimization:**
- **Async Logging:** Log writes don't block execution
- **Atomic State Saves:** Temp file write + rename (one extra write per save, negligible)
- **No Database:** Avoids DB connection overhead and query latency

**Bottleneck Analysis:**
```
Critical Path for 5-Minute Interval:
- Price fetch: 50ms (WebSocket)
- Indicator calculation: 10ms
- Market data fetch: 200ms
- Order submission: 300ms
- Settlement polling: 15s × 20 polls = 300s (longest operation)

Total: ~300s (5 minutes), well within interval window
```

**Scalability Limits:**
- **Single Bot:** Handles 18 trades without performance issues
- **Multi-Market:** Can run up to ~50 concurrent markets on 1 vCPU (limited by API rate limits, not CPU)
- **Historical Data:** Price buffer limited to 60 points (30 minutes); not designed for backtesting

**Monitoring:**
- Log API latency (p50, p95) to detect performance degradation
- Track prediction compute time to ensure <100ms
- Monitor WebSocket disconnect frequency (should be <1/hour)

---

## Appendix: Existing Repository Structure

This is a standalone application. Existing repository structure is not modified.