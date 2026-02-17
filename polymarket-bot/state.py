"""
State Persistence and Logging Module

This module provides comprehensive state management and logging for the Polymarket bot:
- Atomic writes to bot_state.json for crash-safe persistence
- Trade logging to trades.log with append-only audit trail
- Metrics tracking with automatic log rotation
- State recovery and validation

All file operations use atomic writes (temp file + rename) to prevent data corruption
during crashes or interruptions.
"""

import json
import os
import shutil
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from decimal import Decimal

from .models import BotState, Trade

# Configure module logger
logger = logging.getLogger(__name__)

# Default data directory
DATA_DIR = Path("data")

# File paths
STATE_FILE = DATA_DIR / "bot_state.json"
TRADES_LOG = DATA_DIR / "trades.log"
METRICS_LOG = DATA_DIR / "metrics.log"

# Log rotation settings (in bytes)
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
MAX_LOG_BACKUPS = 5


def ensure_data_directory() -> None:
    """
    Ensure the data directory exists.

    Creates the data directory if it doesn't exist. Safe to call multiple times.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Data directory ensured: {DATA_DIR.absolute()}")


def _atomic_write(file_path: Path, content: str) -> None:
    """
    Write content to file atomically using temp file + rename pattern.

    This prevents partial writes and corruption if the process crashes during write.
    The temp file is written first, then atomically renamed to the target path.

    Args:
        file_path: Target file path to write to
        content: String content to write

    Raises:
        IOError: If write or rename operation fails
    """
    ensure_data_directory()

    # Create temp file in same directory for atomic rename
    temp_path = file_path.with_suffix(file_path.suffix + ".tmp")

    try:
        # Write to temp file
        with open(temp_path, 'w', encoding='utf-8') as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())  # Ensure data is written to disk

        # Atomic rename (POSIX guarantees atomicity)
        shutil.move(str(temp_path), str(file_path))
        logger.debug(f"Atomically wrote to {file_path}")

    except Exception as e:
        # Clean up temp file on error
        if temp_path.exists():
            temp_path.unlink()
        logger.error(f"Failed to write {file_path}: {e}")
        raise IOError(f"Atomic write failed for {file_path}: {e}")


def _rotate_log_if_needed(log_path: Path) -> None:
    """
    Rotate log file if it exceeds maximum size.

    Keeps up to MAX_LOG_BACKUPS rotated files with .1, .2, etc. extensions.
    Oldest backup is deleted when limit is reached.

    Args:
        log_path: Path to log file to check and rotate
    """
    if not log_path.exists():
        return

    # Check if rotation is needed
    if log_path.stat().st_size < MAX_LOG_SIZE:
        return

    logger.info(f"Rotating log file {log_path}")

    # Shift existing backups
    for i in range(MAX_LOG_BACKUPS - 1, 0, -1):
        old_backup = Path(f"{log_path}.{i}")
        new_backup = Path(f"{log_path}.{i + 1}")

        if old_backup.exists():
            if i == MAX_LOG_BACKUPS - 1:
                # Delete oldest backup
                old_backup.unlink()
            else:
                shutil.move(str(old_backup), str(new_backup))

    # Rotate current log to .1
    backup_path = Path(f"{log_path}.1")
    shutil.move(str(log_path), str(backup_path))

    logger.info(f"Log rotated to {backup_path}")


def load_state(state_file: Optional[Path] = None) -> BotState:
    """
    Load bot state from JSON file.

    Reads the bot state from bot_state.json. If the file doesn't exist or is invalid,
    returns a default initialized state.

    Args:
        state_file: Optional custom state file path (defaults to STATE_FILE)

    Returns:
        BotState object loaded from file or default state

    Raises:
        ValueError: If state file contains invalid data that can't be parsed
    """
    file_path = state_file or STATE_FILE

    if not file_path.exists():
        logger.info(f"State file not found at {file_path}, returning default state")
        return _create_default_state()

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Parse datetime fields
        for field in ['last_heartbeat', 'created_at', 'updated_at']:
            if field in data and data[field]:
                data[field] = datetime.fromisoformat(data[field])

        # Parse Decimal fields
        decimal_fields = [
            'max_position_size', 'max_total_exposure', 'risk_per_trade',
            'total_pnl', 'current_exposure'
        ]
        for field in decimal_fields:
            if field in data and data[field] is not None:
                data[field] = Decimal(str(data[field]))

        state = BotState(**data)
        logger.info(f"Successfully loaded state from {file_path}")
        return state

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse state file {file_path}: {e}")
        raise ValueError(f"Invalid JSON in state file: {e}")
    except Exception as e:
        logger.error(f"Failed to load state from {file_path}: {e}")
        raise ValueError(f"Failed to load state: {e}")


def save_state(state: BotState, state_file: Optional[Path] = None) -> None:
    """
    Save bot state to JSON file atomically.

    Writes the complete bot state to bot_state.json using atomic write pattern
    to prevent corruption on crashes. Updates the updated_at timestamp.

    Args:
        state: BotState object to persist
        state_file: Optional custom state file path (defaults to STATE_FILE)

    Raises:
        IOError: If atomic write fails
    """
    file_path = state_file or STATE_FILE

    # Update timestamp
    state.updated_at = datetime.utcnow()

    # Serialize to JSON
    data = state.model_dump(mode='json')

    # Convert datetime objects to ISO format strings
    for field in ['last_heartbeat', 'created_at', 'updated_at']:
        if field in data and data[field]:
            if isinstance(data[field], datetime):
                data[field] = data[field].isoformat()

    # Convert Decimal to string for JSON serialization
    decimal_fields = [
        'max_position_size', 'max_total_exposure', 'risk_per_trade',
        'total_pnl', 'current_exposure'
    ]
    for field in decimal_fields:
        if field in data and data[field] is not None:
            data[field] = str(data[field])

    # Write atomically
    content = json.dumps(data, indent=2, ensure_ascii=False)
    _atomic_write(file_path, content)

    logger.info(f"State saved successfully to {file_path}")


def log_trade(trade: Trade, log_file: Optional[Path] = None) -> None:
    """
    Append trade record to trades.log.

    Writes trade as a single JSON line (JSONL format) with timestamp.
    Performs log rotation if file size exceeds limit.

    Args:
        trade: Trade object to log
        log_file: Optional custom log file path (defaults to TRADES_LOG)

    Raises:
        IOError: If append operation fails
    """
    file_path = log_file or TRADES_LOG
    ensure_data_directory()

    # Check if rotation is needed before appending
    _rotate_log_if_needed(file_path)

    # Serialize trade
    trade_data = trade.to_dict()

    # Add logging timestamp
    log_entry = {
        "logged_at": datetime.utcnow().isoformat(),
        "trade": trade_data
    }

    try:
        # Append to log file (JSON Lines format)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            f.flush()
            os.fsync(f.fileno())

        logger.debug(f"Trade {trade.trade_id} logged to {file_path}")

    except Exception as e:
        logger.error(f"Failed to log trade to {file_path}: {e}")
        raise IOError(f"Failed to log trade: {e}")


def log_metrics(metrics: Dict[str, Any], log_file: Optional[Path] = None) -> None:
    """
    Append performance metrics to metrics.log.

    Writes metrics as a single JSON line with timestamp. Performs log rotation
    if file size exceeds limit.

    Args:
        metrics: Dictionary of metrics to log (e.g., cycle number, PnL, win rate)
        log_file: Optional custom log file path (defaults to METRICS_LOG)

    Raises:
        IOError: If append operation fails
    """
    file_path = log_file or METRICS_LOG
    ensure_data_directory()

    # Check if rotation is needed before appending
    _rotate_log_if_needed(file_path)

    # Add timestamp
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "metrics": metrics
    }

    try:
        # Append to log file (JSON Lines format)
        with open(file_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
            f.flush()
            os.fsync(f.fileno())

        logger.debug(f"Metrics logged to {file_path}")

    except Exception as e:
        logger.error(f"Failed to log metrics to {file_path}: {e}")
        raise IOError(f"Failed to log metrics: {e}")


def load_trade_history(log_file: Optional[Path] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Load trade history from trades.log.

    Reads all trade records from the log file. Optionally limits to the most recent N trades.

    Args:
        log_file: Optional custom log file path (defaults to TRADES_LOG)
        limit: Optional maximum number of trades to return (most recent first)

    Returns:
        List of trade records as dictionaries
    """
    file_path = log_file or TRADES_LOG

    if not file_path.exists():
        logger.info(f"Trade log not found at {file_path}")
        return []

    trades = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    log_entry = json.loads(line)
                    trades.append(log_entry)

        # Return most recent first if limit specified
        if limit:
            trades = trades[-limit:]

        logger.info(f"Loaded {len(trades)} trades from {file_path}")
        return trades

    except Exception as e:
        logger.error(f"Failed to load trade history from {file_path}: {e}")
        return []


def load_metrics_history(log_file: Optional[Path] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Load metrics history from metrics.log.

    Reads all metrics records from the log file. Optionally limits to the most recent N entries.

    Args:
        log_file: Optional custom log file path (defaults to METRICS_LOG)
        limit: Optional maximum number of entries to return (most recent first)

    Returns:
        List of metrics records as dictionaries
    """
    file_path = log_file or METRICS_LOG

    if not file_path.exists():
        logger.info(f"Metrics log not found at {file_path}")
        return []

    metrics = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    log_entry = json.loads(line)
                    metrics.append(log_entry)

        # Return most recent first if limit specified
        if limit:
            metrics = metrics[-limit:]

        logger.info(f"Loaded {len(metrics)} metrics entries from {file_path}")
        return metrics

    except Exception as e:
        logger.error(f"Failed to load metrics history from {file_path}: {e}")
        return []


def _create_default_state() -> BotState:
    """
    Create a default bot state for initialization.

    Returns:
        BotState object with sensible defaults
    """
    return BotState(
        bot_id="polymarket_bot_001",
        strategy_name="momentum_rsi_macd",
        max_position_size=Decimal("100.00"),
        max_total_exposure=Decimal("500.00"),
        risk_per_trade=Decimal("20.00")
    )


def clean_temp_files() -> None:
    """
    Clean up any temporary files left over from crashed writes.

    Should be called on bot startup to ensure clean state. Removes any .tmp files
    in the data directory.
    """
    ensure_data_directory()

    temp_files = list(DATA_DIR.glob("*.tmp"))

    if temp_files:
        logger.info(f"Cleaning up {len(temp_files)} temporary files")
        for temp_file in temp_files:
            try:
                temp_file.unlink()
                logger.debug(f"Deleted temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file}: {e}")
    else:
        logger.debug("No temp files to clean up")


def get_state_summary(state: BotState) -> Dict[str, Any]:
    """
    Get a human-readable summary of the bot state.

    Args:
        state: BotState object to summarize

    Returns:
        Dictionary with key state metrics
    """
    win_rate = (
        (state.winning_trades / state.total_trades * 100)
        if state.total_trades > 0
        else 0.0
    )

    return {
        "bot_id": state.bot_id,
        "status": state.status.value,
        "total_trades": state.total_trades,
        "winning_trades": state.winning_trades,
        "win_rate_percent": round(win_rate, 2),
        "total_pnl": float(state.total_pnl),
        "current_exposure": float(state.current_exposure),
        "active_markets_count": len(state.active_markets),
        "last_heartbeat": state.last_heartbeat.isoformat(),
    }
