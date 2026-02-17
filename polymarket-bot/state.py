"""
State Persistence and Logging System

This module provides state management, trade logging, and metrics tracking
for the Polymarket trading bot.

Key Features:
- JSON-based state persistence with atomic writes
- Trade history logging with timestamps
- Metrics tracking (win/loss streaks, drawdown, total trades)
- Crash recovery using temporary files and renames
"""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, Optional, List
from models import BotState, Trade, Position


class StateManager:
    """
    Manages bot state persistence, trade logging, and metrics tracking.

    Uses atomic file writes with temporary files to prevent corruption
    during crashes.
    """

    def __init__(self, state_dir: str = "data"):
        """
        Initialize the state manager.

        Args:
            state_dir: Directory for storing state and log files
        """
        self.state_dir = Path(state_dir)
        self.state_file = self.state_dir / "bot_state.json"
        self.trades_log = self.state_dir / "trades.log"

        # Create state directory if it doesn't exist
        self.state_dir.mkdir(parents=True, exist_ok=True)

        # Initialize metrics
        self._metrics = {
            "win_streak": 0,
            "loss_streak": 0,
            "max_drawdown": Decimal("0.00"),
            "peak_equity": Decimal("0.00"),
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0
        }

    def save_state(self, bot_state: BotState) -> None:
        """
        Save bot state to disk using atomic write operation.

        Uses temporary file + rename pattern to prevent corruption
        on crashes.

        Args:
            bot_state: BotState object to save

        Raises:
            IOError: If state cannot be saved
        """
        temp_file = self.state_file.with_suffix('.tmp')

        try:
            # Write to temporary file first
            with open(temp_file, 'w') as f:
                json.dump(bot_state.to_dict(), f, indent=2)

            # Atomic rename (replaces existing file)
            temp_file.replace(self.state_file)

        except Exception as e:
            # Clean up temporary file on error
            if temp_file.exists():
                temp_file.unlink()
            raise IOError(f"Failed to save state: {e}")

    def load_state(self) -> Optional[Dict[str, Any]]:
        """
        Load bot state from disk.

        Returns:
            Dictionary containing bot state, or None if file doesn't exist

        Raises:
            ValueError: If state file is corrupted
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupted state file: {e}")

    def validate_state(self, state_data: Dict[str, Any]) -> bool:
        """
        Validate loaded state data.

        Args:
            state_data: Dictionary containing state data

        Returns:
            True if state is valid, False otherwise
        """
        required_fields = [
            'bot_id', 'status', 'strategy_name',
            'max_position_size', 'max_total_exposure', 'risk_per_trade'
        ]

        for field in required_fields:
            if field not in state_data:
                return False

        return True

    def log_trade(self, trade: Trade) -> None:
        """
        Append trade to trade history log with timestamp.

        Args:
            trade: Trade object to log

        Raises:
            IOError: If trade cannot be logged
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            log_entry = {
                "timestamp": timestamp,
                "trade": trade.to_dict()
            }

            # Append to log file (creates file if it doesn't exist)
            with open(self.trades_log, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')

        except Exception as e:
            raise IOError(f"Failed to log trade: {e}")

    def load_trades(self) -> List[Dict[str, Any]]:
        """
        Load all trades from trade history log.

        Returns:
            List of trade dictionaries
        """
        if not self.trades_log.exists():
            return []

        trades = []
        try:
            with open(self.trades_log, 'r') as f:
                for line in f:
                    if line.strip():
                        trades.append(json.loads(line))
            return trades
        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupted trades log: {e}")

    def update_metrics(self, trade_result: str, pnl: Decimal, current_equity: Decimal) -> None:
        """
        Update performance metrics based on trade result.

        Args:
            trade_result: "win" or "loss"
            pnl: Profit/loss for the trade
            current_equity: Current total equity
        """
        self._metrics["total_trades"] += 1

        if trade_result.lower() == "win":
            self._metrics["winning_trades"] += 1
            self._metrics["win_streak"] += 1
            self._metrics["loss_streak"] = 0
        else:
            self._metrics["losing_trades"] += 1
            self._metrics["loss_streak"] += 1
            self._metrics["win_streak"] = 0

        # Update peak equity and drawdown
        if current_equity > self._metrics["peak_equity"]:
            self._metrics["peak_equity"] = current_equity

        if self._metrics["peak_equity"] > 0:
            drawdown = (self._metrics["peak_equity"] - current_equity) / self._metrics["peak_equity"]
            if drawdown > self._metrics["max_drawdown"]:
                self._metrics["max_drawdown"] = drawdown

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.

        Returns:
            Dictionary containing current metrics
        """
        return {
            "win_streak": self._metrics["win_streak"],
            "loss_streak": self._metrics["loss_streak"],
            "max_drawdown": float(self._metrics["max_drawdown"]),
            "peak_equity": float(self._metrics["peak_equity"]),
            "total_trades": self._metrics["total_trades"],
            "winning_trades": self._metrics["winning_trades"],
            "losing_trades": self._metrics["losing_trades"],
            "win_rate": self._calculate_win_rate()
        }

    def _calculate_win_rate(self) -> float:
        """Calculate win rate percentage."""
        if self._metrics["total_trades"] == 0:
            return 0.0
        return (self._metrics["winning_trades"] / self._metrics["total_trades"]) * 100

    def reset_metrics(self) -> None:
        """Reset all metrics to initial state."""
        self._metrics = {
            "win_streak": 0,
            "loss_streak": 0,
            "max_drawdown": Decimal("0.00"),
            "peak_equity": Decimal("0.00"),
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0
        }

    def save_metrics(self) -> None:
        """
        Save metrics to disk using atomic write operation.

        Raises:
            IOError: If metrics cannot be saved
        """
        metrics_file = self.state_dir / "metrics.json"
        temp_file = metrics_file.with_suffix('.tmp')

        try:
            # Convert Decimal to float for JSON serialization
            metrics_to_save = {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in self._metrics.items()
            }

            # Write to temporary file first
            with open(temp_file, 'w') as f:
                json.dump(metrics_to_save, f, indent=2)

            # Atomic rename
            temp_file.replace(metrics_file)

        except Exception as e:
            if temp_file.exists():
                temp_file.unlink()
            raise IOError(f"Failed to save metrics: {e}")

    def load_metrics(self) -> None:
        """
        Load metrics from disk.

        Raises:
            ValueError: If metrics file is corrupted
        """
        metrics_file = self.state_dir / "metrics.json"

        if not metrics_file.exists():
            return

        try:
            with open(metrics_file, 'r') as f:
                loaded_metrics = json.load(f)

            # Convert numeric values back to Decimal where appropriate
            self._metrics["win_streak"] = loaded_metrics.get("win_streak", 0)
            self._metrics["loss_streak"] = loaded_metrics.get("loss_streak", 0)
            self._metrics["max_drawdown"] = Decimal(str(loaded_metrics.get("max_drawdown", "0.00")))
            self._metrics["peak_equity"] = Decimal(str(loaded_metrics.get("peak_equity", "0.00")))
            self._metrics["total_trades"] = loaded_metrics.get("total_trades", 0)
            self._metrics["winning_trades"] = loaded_metrics.get("winning_trades", 0)
            self._metrics["losing_trades"] = loaded_metrics.get("losing_trades", 0)

        except json.JSONDecodeError as e:
            raise ValueError(f"Corrupted metrics file: {e}")


def create_state_manager(state_dir: str = "data") -> StateManager:
    """
    Helper function to create a StateManager instance.

    Args:
        state_dir: Directory for storing state and log files

    Returns:
        Initialized StateManager instance
    """
    return StateManager(state_dir)


def recover_state(state_manager: StateManager) -> Optional[Dict[str, Any]]:
    """
    Attempt to recover state from disk after a crash.

    Args:
        state_manager: StateManager instance

    Returns:
        Recovered state dictionary, or None if recovery fails
    """
    try:
        state_data = state_manager.load_state()

        if state_data and state_manager.validate_state(state_data):
            return state_data

        return None

    except (ValueError, IOError) as e:
        print(f"State recovery failed: {e}")
        return None
