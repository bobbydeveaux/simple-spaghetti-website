"""
Main Orchestrator for Polymarket Trading Bot.

This module implements the main event loop orchestrator that:
- Manages 18-cycle event loop with 5-minute intervals (90 minutes total)
- Coordinates sequential pipeline execution (data → predict → risk → allocate → execute → log)
- Handles graceful shutdown on SIGINT/SIGTERM signals
- Implements crash recovery from persisted state
- Logs all trading activity and metrics

The bot runs for a fixed 18 cycles (90 minutes) and automatically shuts down
after completion or when critical risk thresholds are breached.
"""

import signal
import sys
import time
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from pathlib import Path

from config import Config, get_config
from models import BotState, BotStatus, Trade, SignalType
from market_data import BinanceWebSocketClient, PolymarketClient, get_market_data
from prediction import PredictionEngine
from risk import RiskController
from capital import CapitalAllocator
from state import StateManager


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('polymarket_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TradingOrchestrator:
    """
    Main orchestrator for the Polymarket trading bot.

    Manages the complete trading lifecycle including:
    - Component initialization
    - Event loop execution
    - Pipeline coordination
    - Shutdown handling
    - State persistence
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the trading orchestrator.

        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config if config else get_config()
        self.should_shutdown = False
        self.shutdown_reason = None

        # Initialize components
        self.binance_client: Optional[BinanceWebSocketClient] = None
        self.polymarket_client: Optional[PolymarketClient] = None
        self.prediction_engine: Optional[PredictionEngine] = None
        self.risk_controller: Optional[RiskController] = None
        self.capital_allocator: Optional[CapitalAllocator] = None
        self.state_manager: Optional[StateManager] = None

        # Bot state
        self.bot_state: Optional[BotState] = None
        self.current_cycle = 0
        self.total_cycles = 18
        self.cycle_interval = 300  # 5 minutes in seconds

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("TradingOrchestrator initialized")

    def _signal_handler(self, signum, frame):
        """
        Handle shutdown signals (SIGINT/SIGTERM).

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        signal_name = 'SIGINT' if signum == signal.SIGINT else 'SIGTERM'
        logger.warning(f"Received {signal_name} signal, initiating graceful shutdown...")
        self.should_shutdown = True
        self.shutdown_reason = f"Signal {signal_name} received"

    def initialize_components(self) -> bool:
        """
        Initialize all trading components.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing trading components...")

            # Initialize state manager first (needed for recovery)
            self.state_manager = StateManager(state_dir=self.config.state_dir)
            logger.info("State manager initialized")

            # Initialize Binance WebSocket for BTC price feed
            self.binance_client = BinanceWebSocketClient(buffer_size=100)
            self.binance_client.connect()
            logger.info("Binance WebSocket connected")

            # Wait for initial price data
            time.sleep(2)
            if len(self.binance_client.get_latest_prices(1)) == 0:
                logger.error("Failed to receive initial price data from Binance")
                return False

            # Initialize Polymarket client
            self.polymarket_client = PolymarketClient(self.config)
            logger.info("Polymarket client initialized")

            # Initialize prediction engine
            self.prediction_engine = PredictionEngine(self.config)
            logger.info("Prediction engine initialized")

            # Initialize risk controller
            self.risk_controller = RiskController(
                max_drawdown=self.config.max_drawdown,
                max_volatility=self.config.max_volatility,
                starting_capital=Decimal(str(self.config.starting_capital))
            )
            logger.info("Risk controller initialized")

            # Initialize capital allocator
            self.capital_allocator = CapitalAllocator(
                base_size=Decimal(str(self.config.base_position_size)),
                multiplier=Decimal("1.5"),
                max_size=Decimal(str(self.config.max_position_size))
            )
            logger.info("Capital allocator initialized")

            logger.info("All components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize components: {e}", exc_info=True)
            return False

    def load_or_create_bot_state(self) -> BotState:
        """
        Load existing bot state or create new one.

        Returns:
            BotState object
        """
        # Try to load existing state
        state_data = self.state_manager.load_state()

        if state_data:
            logger.info("Loaded existing bot state from disk")
            # Reconstruct BotState from saved data
            # For now, create new state (can extend to support full recovery)
            self.current_cycle = state_data.get('current_cycle', 0)

        # Create new bot state
        bot_state = BotState(
            bot_id=f"polymarket_bot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            status=BotStatus.INITIALIZING,
            strategy_name="rsi_macd_momentum",
            max_position_size=Decimal(str(self.config.max_position_size)),
            max_total_exposure=Decimal(str(self.config.max_total_exposure)),
            risk_per_trade=Decimal(str(self.config.base_position_size)),
            active_markets=[],
            total_trades=0,
            winning_trades=0,
            total_pnl=Decimal("0.00"),
            current_exposure=Decimal("0.00"),
            api_key_active=True,
            last_heartbeat=datetime.now(timezone.utc),
            error_message=None
        )

        return bot_state

    def save_bot_state(self):
        """Save current bot state to disk."""
        if self.bot_state and self.state_manager:
            try:
                state_dict = self.bot_state.model_dump()
                state_dict['current_cycle'] = self.current_cycle
                # Convert datetime to string for JSON serialization
                state_dict['last_heartbeat'] = state_dict['last_heartbeat'].isoformat()
                self.state_manager.save_state(type('obj', (object,), {'to_dict': lambda: state_dict})())
                logger.debug("Bot state saved to disk")
            except Exception as e:
                logger.error(f"Failed to save bot state: {e}")

    def run_trading_cycle(self, cycle_number: int) -> bool:
        """
        Execute a single trading cycle.

        Pipeline:
        1. Fetch market data (BTC price, indicators, Polymarket odds)
        2. Generate prediction signal
        3. Check risk constraints
        4. Calculate position size
        5. Execute trade (simulated for now)
        6. Log results

        Args:
            cycle_number: Current cycle number (1-18)

        Returns:
            True if cycle completed successfully, False on critical failure
        """
        try:
            logger.info(f"=== Cycle {cycle_number}/18 Started ===")

            # Update bot status
            self.bot_state.status = BotStatus.RUNNING
            self.bot_state.last_heartbeat = datetime.now(timezone.utc)

            # Step 1: Fetch market data
            logger.info("Step 1: Fetching market data...")
            try:
                market_data = get_market_data(
                    self.binance_client,
                    self.polymarket_client,
                    market_id=None  # Auto-discover active BTC market
                )
                logger.info(
                    f"Market data fetched - BTC: ${market_data.metadata.get('btc_price', 'N/A'):.2f}, "
                    f"Market: {market_data.market_id[:8]}..."
                )
            except Exception as e:
                logger.error(f"Failed to fetch market data: {e}")
                return True  # Non-critical, continue to next cycle

            # Step 2: Generate prediction signal
            logger.info("Step 2: Generating prediction signal...")
            try:
                prices = self.binance_client.get_latest_prices(100)
                btc_price = prices[-1] if prices else None
                prediction_signal = self.prediction_engine.generate_signal(prices, btc_price)
                logger.info(
                    f"Signal: {prediction_signal.signal.value.upper()} "
                    f"(confidence: {prediction_signal.confidence:.2f}) - {prediction_signal.reasoning}"
                )
            except Exception as e:
                logger.error(f"Failed to generate prediction signal: {e}")
                return True  # Non-critical, continue to next cycle

            # Skip if signal is SKIP
            if prediction_signal.signal == SignalType.SKIP:
                logger.info("Signal is SKIP, no trade executed")
                return True

            # Step 3: Check risk constraints
            logger.info("Step 3: Checking risk constraints...")
            try:
                # Calculate current capital
                current_capital = Decimal(str(self.config.starting_capital)) + self.bot_state.total_pnl

                # Check drawdown
                risk_approved = self.risk_controller.check_risk(
                    current_capital=current_capital,
                    price_history=prices,
                    market_data=market_data
                )

                if not risk_approved:
                    logger.warning("Risk check failed, trade rejected")

                    # Check if critical drawdown
                    drawdown = self.risk_controller.calculate_drawdown(
                        current_capital,
                        self.risk_controller.starting_capital
                    )
                    if drawdown >= self.config.max_drawdown:
                        logger.critical(f"Maximum drawdown reached: {drawdown:.2%}")
                        self.should_shutdown = True
                        self.shutdown_reason = "Maximum drawdown threshold breached"
                        return False  # Critical failure

                    return True  # Non-critical, continue to next cycle

                logger.info("Risk checks passed")
            except Exception as e:
                logger.error(f"Risk check failed: {e}")
                return True  # Non-critical, continue to next cycle

            # Step 4: Calculate position size
            logger.info("Step 4: Calculating position size...")
            try:
                # Get win streak from state manager metrics
                metrics = self.state_manager.get_metrics()
                win_streak = metrics.get('win_streak', 0)

                position_size = self.capital_allocator.calculate_position_size(
                    win_streak=win_streak,
                    current_capital=current_capital
                )
                logger.info(f"Position size calculated: ${position_size:.2f} (win streak: {win_streak})")
            except Exception as e:
                logger.error(f"Failed to calculate position size: {e}")
                return True  # Non-critical, continue to next cycle

            # Step 5: Execute trade (SIMULATED for now - no real Polymarket orders)
            logger.info("Step 5: Executing trade (SIMULATED)...")
            try:
                # Simulate trade execution
                direction = "YES" if prediction_signal.signal == SignalType.UP else "NO"
                logger.info(f"SIMULATED: Placing {direction} order for ${position_size:.2f} on market {market_data.market_id[:8]}...")

                # Simulate outcome (random for now - in production would be actual settlement)
                import random
                outcome = "WIN" if random.random() > 0.5 else "LOSS"

                # Calculate P&L (simplified - in production would be based on actual odds)
                odds = market_data.yes_price if direction == "YES" else market_data.no_price
                pnl = position_size * (odds - Decimal("1.0")) if outcome == "WIN" else -position_size

                logger.info(f"Trade outcome: {outcome}, P&L: ${pnl:.2f}")

                # Update bot state
                self.bot_state.total_trades += 1
                if outcome == "WIN":
                    self.bot_state.winning_trades += 1
                self.bot_state.total_pnl += pnl

                # Update state manager metrics
                self.state_manager.update_metrics(outcome.lower(), pnl, current_capital + pnl)

                # Log trade
                trade = Trade(
                    trade_id=f"trade_{self.bot_state.total_trades}",
                    bot_id=self.bot_state.bot_id,
                    market_id=market_data.market_id,
                    timestamp=datetime.now(timezone.utc),
                    side=direction,
                    size=position_size,
                    status="executed",
                    outcome=outcome,
                    pnl=pnl,
                    signal_type=prediction_signal.signal,
                    confidence=prediction_signal.confidence
                )
                self.state_manager.log_trade(trade)

                logger.info(f"Trade logged: {trade.trade_id}")

            except Exception as e:
                logger.error(f"Trade execution failed: {e}")
                return True  # Non-critical, continue to next cycle

            # Step 6: Save state
            logger.info("Step 6: Saving bot state...")
            self.save_bot_state()
            self.state_manager.save_metrics()

            logger.info(
                f"=== Cycle {cycle_number}/18 Completed === "
                f"Total P&L: ${self.bot_state.total_pnl:.2f}, "
                f"Win Rate: {self.bot_state.winning_trades}/{self.bot_state.total_trades}"
            )

            return True

        except Exception as e:
            logger.error(f"Unexpected error in trading cycle: {e}", exc_info=True)
            return True  # Continue to next cycle even on unexpected errors

    def shutdown(self, reason: str):
        """
        Perform graceful shutdown.

        Args:
            reason: Reason for shutdown
        """
        logger.info(f"Shutting down: {reason}")

        # Update bot status
        if self.bot_state:
            self.bot_state.status = BotStatus.STOPPED
            self.bot_state.last_heartbeat = datetime.now(timezone.utc)
            self.save_bot_state()

        # Close connections
        if self.binance_client:
            try:
                self.binance_client.close()
                logger.info("Binance WebSocket closed")
            except Exception as e:
                logger.error(f"Error closing Binance WebSocket: {e}")

        if self.polymarket_client:
            try:
                self.polymarket_client.close()
                logger.info("Polymarket client closed")
            except Exception as e:
                logger.error(f"Error closing Polymarket client: {e}")

        # Save final metrics
        if self.state_manager:
            try:
                self.state_manager.save_metrics()
                logger.info("Final metrics saved")
            except Exception as e:
                logger.error(f"Error saving final metrics: {e}")

        # Print final summary
        if self.bot_state:
            logger.info("=" * 60)
            logger.info("FINAL SUMMARY")
            logger.info("=" * 60)
            logger.info(f"Total Cycles: {self.current_cycle}/{self.total_cycles}")
            logger.info(f"Total Trades: {self.bot_state.total_trades}")
            logger.info(f"Winning Trades: {self.bot_state.winning_trades}")
            win_rate = (self.bot_state.winning_trades / self.bot_state.total_trades * 100) if self.bot_state.total_trades > 0 else 0
            logger.info(f"Win Rate: {win_rate:.1f}%")
            logger.info(f"Total P&L: ${self.bot_state.total_pnl:.2f}")
            starting_capital = Decimal(str(self.config.starting_capital))
            final_capital = starting_capital + self.bot_state.total_pnl
            roi = (self.bot_state.total_pnl / starting_capital * 100) if starting_capital > 0 else 0
            logger.info(f"Final Capital: ${final_capital:.2f}")
            logger.info(f"ROI: {roi:.2f}%")
            logger.info(f"Shutdown Reason: {reason}")
            logger.info("=" * 60)

        logger.info("Shutdown complete")

    def run(self):
        """
        Main event loop.

        Executes 18 trading cycles with 5-minute intervals.
        Handles graceful shutdown and crash recovery.
        """
        logger.info("=" * 60)
        logger.info("POLYMARKET TRADING BOT STARTED")
        logger.info("=" * 60)

        # Initialize components
        if not self.initialize_components():
            logger.critical("Component initialization failed, exiting")
            sys.exit(1)

        # Load or create bot state
        self.bot_state = self.load_or_create_bot_state()
        logger.info(f"Bot ID: {self.bot_state.bot_id}")
        logger.info(f"Strategy: {self.bot_state.strategy_name}")
        logger.info(f"Starting Capital: ${self.config.starting_capital:.2f}")
        logger.info(f"Cycles: {self.total_cycles} x {self.cycle_interval}s = {self.total_cycles * self.cycle_interval / 60:.0f} minutes")

        # Main event loop
        try:
            for cycle in range(self.current_cycle + 1, self.total_cycles + 1):
                if self.should_shutdown:
                    break

                self.current_cycle = cycle

                # Run trading cycle
                success = self.run_trading_cycle(cycle)

                if not success:
                    # Critical failure, shutdown
                    break

                # Sleep until next cycle (unless it's the last cycle or shutdown requested)
                if cycle < self.total_cycles and not self.should_shutdown:
                    logger.info(f"Waiting {self.cycle_interval}s until next cycle...")

                    # Sleep in smaller intervals to allow for responsive shutdown
                    for _ in range(self.cycle_interval):
                        if self.should_shutdown:
                            break
                        time.sleep(1)

            # Determine shutdown reason
            if self.should_shutdown and self.shutdown_reason:
                reason = self.shutdown_reason
            elif self.current_cycle >= self.total_cycles:
                reason = "All 18 cycles completed successfully"
            else:
                reason = "Event loop terminated"

            self.shutdown(reason)

        except KeyboardInterrupt:
            logger.warning("Keyboard interrupt received")
            self.shutdown("Keyboard interrupt")
        except Exception as e:
            logger.critical(f"Unexpected error in main event loop: {e}", exc_info=True)
            self.shutdown(f"Unexpected error: {e}")
            sys.exit(1)


def main():
    """Entry point for the Polymarket trading bot."""
    orchestrator = TradingOrchestrator()
    orchestrator.run()


if __name__ == "__main__":
    main()
