"""
Main Orchestrator for Polymarket Trading Bot.

This module implements the main event loop that coordinates all bot components:
- Market data fetching (Binance + Polymarket)
- Signal generation (prediction engine)
- Risk validation (drawdown, volatility checks)
- Position sizing (win-streak based capital allocation)
- Trade execution (order submission and settlement)
- State persistence (logging and recovery)

The bot runs for 18 cycles with 5-minute intervals between each cycle.
It automatically halts if max drawdown (30%) is exceeded or on critical errors.
"""

import logging
import time
import sys
from typing import Optional, Dict, Any
from decimal import Decimal
from datetime import datetime, timezone

from .config import Config, get_config, ConfigurationError
from .models import BotState, BotStatus, SignalType
from .market_data import BinanceWebSocketClient, PolymarketClient, get_market_data
from .prediction import PredictionEngine
from .risk import RiskManager
from .capital import CapitalAllocator
from .execution import TradeExecutor, ExecutionError
from .state import StateManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('polymarket_bot.log')
    ]
)

logger = logging.getLogger(__name__)


class TradingBot:
    """
    Main trading bot orchestrator.

    Manages the complete trading lifecycle including initialization,
    event loop execution, and graceful shutdown.
    """

    # Constants
    TOTAL_CYCLES = 18
    CYCLE_INTERVAL_SECONDS = 300  # 5 minutes
    STARTING_CAPITAL = Decimal("100.0")

    def __init__(self, config: Optional[Config] = None, dry_run: bool = False):
        """
        Initialize the trading bot.

        Args:
            config: Configuration object. If None, loads from environment.
            dry_run: If True, runs in simulation mode (no real orders)
        """
        self.config = config if config else get_config()
        self.dry_run = dry_run

        # Initialize components
        self.binance_client: Optional[BinanceWebSocketClient] = None
        self.polymarket_client: Optional[PolymarketClient] = None
        self.prediction_engine: Optional[PredictionEngine] = None
        self.risk_manager: Optional[RiskManager] = None
        self.capital_allocator: Optional[CapitalAllocator] = None
        self.trade_executor: Optional[TradeExecutor] = None
        self.state_manager: Optional[StateManager] = None

        # Bot state tracking
        self.current_capital = self.STARTING_CAPITAL
        self.win_streak = 0
        self.total_trades = 0
        self.is_running = False

        logger.info(
            f"TradingBot initialized (dry_run={dry_run}, "
            f"starting_capital=${self.STARTING_CAPITAL})"
        )

    def initialize(self) -> bool:
        """
        Initialize all bot components.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing bot components...")

            # Initialize state manager
            self.state_manager = StateManager(state_dir="data")

            # Try to recover previous state
            previous_state = self.state_manager.load_state()
            if previous_state:
                logger.info("Found previous state, checking if resumable...")
                # For now, always start fresh (can implement resume logic later)
                logger.info("Starting fresh session")

            # Initialize Binance WebSocket
            self.binance_client = BinanceWebSocketClient(buffer_size=100)
            self.binance_client.connect()
            logger.info("Binance WebSocket connected")

            # Wait for price buffer to fill
            logger.info("Waiting for price buffer to populate...")
            time.sleep(10)  # Give WebSocket time to accumulate data

            # Initialize Polymarket client
            self.polymarket_client = PolymarketClient(self.config)
            logger.info("Polymarket client initialized")

            # Initialize prediction engine
            self.prediction_engine = PredictionEngine(self.config)
            logger.info("Prediction engine initialized")

            # Initialize risk manager
            self.risk_manager = RiskManager(
                starting_capital=self.STARTING_CAPITAL
            )
            logger.info("Risk manager initialized")

            # Initialize capital allocator
            self.capital_allocator = CapitalAllocator()
            logger.info("Capital allocator initialized")

            # Initialize trade executor (not in dry run)
            if not self.dry_run:
                self.trade_executor = TradeExecutor(self.config)
                logger.info("Trade executor initialized")
            else:
                logger.info("Running in DRY RUN mode - no real trades")

            logger.info("All components initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Initialization failed: {e}", exc_info=True)
            return False

    def run(self) -> None:
        """
        Run the main trading loop for 18 cycles.

        Each cycle:
        1. Fetches market data
        2. Generates prediction signal
        3. Validates risk constraints
        4. Calculates position size
        5. Executes trade (if signal not SKIP)
        6. Updates state and logs results

        Halts on critical errors or max drawdown breach.
        """
        if not self.initialize():
            logger.error("Initialization failed, cannot start trading")
            return

        self.is_running = True
        logger.info(f"Starting trading bot for {self.TOTAL_CYCLES} cycles...")

        for cycle in range(1, self.TOTAL_CYCLES + 1):
            try:
                logger.info(f"\n{'=' * 60}")
                logger.info(f"CYCLE {cycle}/{self.TOTAL_CYCLES}")
                logger.info(f"{'=' * 60}")

                # Execute trading cycle
                success = self.run_trading_cycle(cycle)

                if not success:
                    logger.error(f"Cycle {cycle} failed, halting bot")
                    self.shutdown("Critical error in trading cycle")
                    return

                # Check if we've completed all cycles
                if cycle >= self.TOTAL_CYCLES:
                    logger.info(f"Completed all {self.TOTAL_CYCLES} cycles")
                    break

                # Wait for next cycle (skip wait on last cycle)
                if cycle < self.TOTAL_CYCLES:
                    logger.info(
                        f"Waiting {self.CYCLE_INTERVAL_SECONDS}s for next cycle..."
                    )
                    time.sleep(self.CYCLE_INTERVAL_SECONDS)

            except KeyboardInterrupt:
                logger.info("Received interrupt signal, shutting down...")
                self.shutdown("User interrupt")
                return

            except Exception as e:
                logger.error(f"Unexpected error in cycle {cycle}: {e}", exc_info=True)
                self.shutdown("Unexpected error")
                return

        # Normal completion
        self.shutdown("Completed successfully")

    def run_trading_cycle(self, cycle_number: int) -> bool:
        """
        Execute a single trading cycle.

        Args:
            cycle_number: Current cycle number (1-18)

        Returns:
            True if cycle completed successfully, False on critical failure
        """
        try:
            # Step 1: Fetch market data
            logger.info("Step 1: Fetching market data...")
            market_data = get_market_data(
                self.binance_client,
                self.polymarket_client
            )
            logger.info(
                f"Market data fetched - BTC: ${market_data.metadata.get('btc_price'):.2f}"
            )

            # Step 2: Generate prediction signal
            logger.info("Step 2: Generating prediction signal...")
            prices = self.binance_client.get_latest_prices(100)
            btc_price = self.binance_client.get_latest_price()

            signal = self.prediction_engine.generate_signal(
                prices=prices,
                btc_price=btc_price
            )

            logger.info(
                f"Signal: {signal.signal.value.upper()} "
                f"(confidence: {signal.confidence:.2f})"
            )
            logger.info(f"Reasoning: {signal.reasoning}")

            # Step 3: Check if we should skip this cycle
            if signal.signal == SignalType.SKIP:
                logger.info("Skipping trade - no clear signal")
                return True

            # Step 4: Risk validation
            logger.info("Step 3: Validating risk constraints...")

            # Check drawdown
            drawdown_ok, current_drawdown = self.risk_manager.check_drawdown(
                self.current_capital
            )

            logger.info(f"Current drawdown: {current_drawdown:.2f}%")

            if not drawdown_ok:
                logger.error(
                    f"DRAWDOWN LIMIT EXCEEDED: {current_drawdown:.2f}% > "
                    f"{self.risk_manager.max_drawdown_percent}%"
                )
                return False

            # Check volatility
            volatility_ok, volatility = self.risk_manager.check_volatility(prices[-5:])

            logger.info(f"Current 5-min volatility: {volatility:.2f}%")

            if not volatility_ok:
                logger.warning(
                    f"High volatility detected: {volatility:.2f}%, skipping trade"
                )
                return True

            # Step 5: Calculate position size
            logger.info("Step 4: Calculating position size...")
            position_size = self.capital_allocator.calculate_position_size(
                win_streak=self.win_streak,
                current_capital=self.current_capital
            )

            logger.info(
                f"Position size: ${position_size:.2f} "
                f"(win streak: {self.win_streak})"
            )

            # Step 6: Execute trade
            logger.info("Step 5: Executing trade...")

            if self.dry_run:
                # Simulate trade execution
                logger.info("[DRY RUN] Simulating trade execution...")
                outcome, pnl = self._simulate_trade(signal.signal, position_size)
                order_id = f"DRY_RUN_{cycle_number}"
            else:
                # Real trade execution
                order_id = self.trade_executor.submit_order(
                    market_id=market_data.market_id,
                    signal=signal.signal,
                    size=position_size
                )

                logger.info(f"Order submitted: {order_id}")

                # Poll for settlement
                outcome, pnl = self.trade_executor.poll_settlement(
                    order_id,
                    timeout=300
                )

            logger.info(f"Trade result: {outcome}, PnL: ${pnl:.2f}")

            # Step 7: Update state
            self.total_trades += 1
            self.current_capital += pnl

            if outcome == "WIN":
                self.win_streak += 1
            else:
                self.win_streak = 0

            # Log trade to state manager
            self.state_manager.update_metrics(
                trade_result=outcome,
                pnl=pnl,
                current_equity=self.current_capital
            )

            # Save metrics
            self.state_manager.save_metrics()

            logger.info(
                f"Updated state - Capital: ${self.current_capital:.2f}, "
                f"Win streak: {self.win_streak}, "
                f"Total trades: {self.total_trades}"
            )

            return True

        except ExecutionError as e:
            logger.error(f"Trade execution failed: {e}")
            # Execution errors are recoverable, skip this cycle
            return True

        except Exception as e:
            logger.error(f"Critical error in trading cycle: {e}", exc_info=True)
            return False

    def _simulate_trade(
        self,
        signal: SignalType,
        position_size: Decimal
    ) -> tuple[str, Decimal]:
        """
        Simulate trade execution for dry run mode.

        Args:
            signal: Trading signal (UP or DOWN)
            position_size: Position size in USD

        Returns:
            Tuple of (outcome, pnl)
        """
        import random

        # Simulate 60% win rate
        is_win = random.random() < 0.6

        if is_win:
            # Simulate typical odds payout (1.5x - 2x)
            multiplier = Decimal(str(1.5 + random.random() * 0.5))
            pnl = position_size * (multiplier - Decimal("1.0"))
            outcome = "WIN"
        else:
            # Loss = lose position size
            pnl = -position_size
            outcome = "LOSS"

        logger.info(f"[DRY RUN] Simulated {outcome}: ${pnl:.2f}")
        return outcome, pnl

    def shutdown(self, reason: str) -> None:
        """
        Gracefully shutdown the bot.

        Args:
            reason: Reason for shutdown
        """
        logger.info(f"Shutting down bot: {reason}")

        self.is_running = False

        # Close WebSocket connections
        if self.binance_client:
            try:
                self.binance_client.close()
                logger.info("Binance WebSocket closed")
            except Exception as e:
                logger.error(f"Error closing Binance WebSocket: {e}")

        # Close Polymarket client
        if self.polymarket_client:
            try:
                self.polymarket_client.close()
                logger.info("Polymarket client closed")
            except Exception as e:
                logger.error(f"Error closing Polymarket client: {e}")

        # Close trade executor
        if self.trade_executor:
            try:
                self.trade_executor.close()
                logger.info("Trade executor closed")
            except Exception as e:
                logger.error(f"Error closing trade executor: {e}")

        # Final metrics report
        if self.state_manager:
            metrics = self.state_manager.get_metrics()
            logger.info("\n" + "=" * 60)
            logger.info("FINAL PERFORMANCE METRICS")
            logger.info("=" * 60)
            logger.info(f"Total Trades: {metrics['total_trades']}")
            logger.info(f"Winning Trades: {metrics['winning_trades']}")
            logger.info(f"Losing Trades: {metrics['losing_trades']}")
            logger.info(f"Win Rate: {metrics['win_rate']:.2f}%")
            logger.info(f"Final Capital: ${self.current_capital:.2f}")
            logger.info(f"Total PnL: ${self.current_capital - self.STARTING_CAPITAL:.2f}")
            logger.info(f"Max Drawdown: {metrics['max_drawdown']:.2f}%")
            logger.info("=" * 60)

        logger.info("Bot shutdown complete")


def main(dry_run: bool = False) -> None:
    """
    Main entry point for the trading bot.

    Args:
        dry_run: If True, runs in simulation mode (no real orders)
    """
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = get_config()

        # Create and run bot
        bot = TradingBot(config=config, dry_run=dry_run)
        bot.run()

    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Polymarket Trading Bot")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run in simulation mode (no real trades)"
    )
    parser.add_argument(
        "--log-level",
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
        default='INFO',
        help="Set logging level"
    )

    args = parser.parse_args()

    # Update logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Run bot
    main(dry_run=args.dry_run)
