"""
Test suite for state persistence module.

Tests state saving/loading, atomic writes, trade logging, metrics logging,
file rotation, and crash recovery.
"""

import json
import os
import pytest
import tempfile
import shutil
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from state import (
    load_state,
    save_state,
    log_trade,
    log_metrics,
    load_trade_history,
    load_metrics_history,
    clean_temp_files,
    get_state_summary,
    ensure_data_directory,
    _atomic_write,
    _rotate_log_if_needed,
    _create_default_state,
    MAX_LOG_SIZE,
    MAX_LOG_BACKUPS
)
from models import BotState, Trade, BotStatus, OrderSide, OrderType, TradeStatus, OutcomeType


@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_bot_state():
    """Create a sample BotState for testing."""
    return BotState(
        bot_id="test_bot_001",
        status=BotStatus.RUNNING,
        strategy_name="test_strategy",
        max_position_size=Decimal("1000.00"),
        max_total_exposure=Decimal("5000.00"),
        risk_per_trade=Decimal("100.00"),
        total_trades=10,
        winning_trades=6,
        total_pnl=Decimal("250.50"),
        current_exposure=Decimal("1500.00"),
        active_markets=["market_1", "market_2"]
    )


@pytest.fixture
def sample_trade():
    """Create a sample Trade for testing."""
    return Trade(
        trade_id="trade_001",
        market_id="market_123",
        order_id="order_456",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        outcome=OutcomeType.YES,
        price=Decimal("0.65"),
        quantity=Decimal("100"),
        filled_quantity=Decimal("100"),
        status=TradeStatus.EXECUTED,
        fee=Decimal("0.50")
    )


class TestDataDirectoryManagement:
    """Test suite for data directory management."""

    def test_ensure_data_directory_creates_dir(self, temp_data_dir):
        """Test that ensure_data_directory creates the directory if it doesn't exist."""
        test_dir = temp_data_dir / "test_data"
        assert not test_dir.exists()

        # Temporarily patch DATA_DIR
        with patch('state.DATA_DIR', test_dir):
            ensure_data_directory()
            assert test_dir.exists()
            assert test_dir.is_dir()

    def test_ensure_data_directory_idempotent(self, temp_data_dir):
        """Test that ensure_data_directory can be called multiple times safely."""
        test_dir = temp_data_dir / "test_data"

        with patch('state.DATA_DIR', test_dir):
            ensure_data_directory()
            ensure_data_directory()  # Should not raise error
            assert test_dir.exists()


class TestAtomicWrites:
    """Test suite for atomic write operations."""

    def test_atomic_write_creates_file(self, temp_data_dir):
        """Test that atomic write successfully creates a file."""
        test_file = temp_data_dir / "test.json"
        content = '{"test": "data"}'

        with patch('state.DATA_DIR', temp_data_dir):
            _atomic_write(test_file, content)

        assert test_file.exists()
        assert test_file.read_text() == content

    def test_atomic_write_overwrites_existing(self, temp_data_dir):
        """Test that atomic write overwrites existing file."""
        test_file = temp_data_dir / "test.json"
        test_file.write_text("old data")

        new_content = '{"test": "new data"}'
        with patch('state.DATA_DIR', temp_data_dir):
            _atomic_write(test_file, new_content)

        assert test_file.read_text() == new_content

    def test_atomic_write_cleans_temp_on_error(self, temp_data_dir):
        """Test that temp file is cleaned up if write fails."""
        test_file = temp_data_dir / "test.json"
        temp_file = test_file.with_suffix(test_file.suffix + ".tmp")

        with patch('state.DATA_DIR', temp_data_dir):
            # Mock shutil.move to raise an error
            with patch('state.shutil.move', side_effect=Exception("Move failed")):
                with pytest.raises(IOError, match="Atomic write failed"):
                    _atomic_write(test_file, "content")

                # Temp file should be cleaned up
                assert not temp_file.exists()

    def test_atomic_write_simulated_crash(self, temp_data_dir):
        """Test that partial writes don't corrupt the original file."""
        test_file = temp_data_dir / "test.json"
        original_content = '{"original": "data"}'
        test_file.write_text(original_content)

        with patch('state.DATA_DIR', temp_data_dir):
            # Simulate crash during write by raising exception
            with patch('builtins.open', side_effect=Exception("Simulated crash")):
                with pytest.raises(Exception):
                    _atomic_write(test_file, "new content")

            # Original file should remain unchanged
            assert test_file.read_text() == original_content


class TestStatePersistence:
    """Test suite for state save/load operations."""

    def test_save_and_load_state_roundtrip(self, temp_data_dir, sample_bot_state):
        """Test that state can be saved and loaded correctly."""
        state_file = temp_data_dir / "bot_state.json"

        with patch('state.STATE_FILE', state_file):
            with patch('state.DATA_DIR', temp_data_dir):
                save_state(sample_bot_state, state_file)
                loaded_state = load_state(state_file)

        assert loaded_state.bot_id == sample_bot_state.bot_id
        assert loaded_state.status == sample_bot_state.status
        assert loaded_state.total_trades == sample_bot_state.total_trades
        assert loaded_state.winning_trades == sample_bot_state.winning_trades
        assert loaded_state.total_pnl == sample_bot_state.total_pnl
        assert loaded_state.current_exposure == sample_bot_state.current_exposure
        assert loaded_state.active_markets == sample_bot_state.active_markets

    def test_load_state_creates_default_if_missing(self, temp_data_dir):
        """Test that load_state returns default state if file doesn't exist."""
        state_file = temp_data_dir / "nonexistent_state.json"

        loaded_state = load_state(state_file)

        assert loaded_state.bot_id is not None
        assert loaded_state.strategy_name is not None
        assert loaded_state.total_trades == 0
        assert loaded_state.winning_trades == 0

    def test_load_state_handles_invalid_json(self, temp_data_dir):
        """Test that load_state raises error for invalid JSON."""
        state_file = temp_data_dir / "invalid_state.json"
        state_file.write_text("not valid json {")

        with pytest.raises(ValueError, match="Invalid JSON"):
            load_state(state_file)

    def test_save_state_updates_timestamp(self, temp_data_dir, sample_bot_state):
        """Test that save_state updates the updated_at timestamp."""
        state_file = temp_data_dir / "bot_state.json"
        original_updated_at = sample_bot_state.updated_at

        with patch('state.DATA_DIR', temp_data_dir):
            save_state(sample_bot_state, state_file)

        # The state object should have updated timestamp
        assert sample_bot_state.updated_at > original_updated_at

    def test_save_state_preserves_decimal_precision(self, temp_data_dir, sample_bot_state):
        """Test that Decimal fields maintain precision after save/load."""
        state_file = temp_data_dir / "bot_state.json"

        with patch('state.DATA_DIR', temp_data_dir):
            save_state(sample_bot_state, state_file)
            loaded_state = load_state(state_file)

        assert loaded_state.total_pnl == Decimal("250.50")
        assert loaded_state.max_position_size == Decimal("1000.00")

    def test_state_file_is_valid_json(self, temp_data_dir, sample_bot_state):
        """Test that saved state file is valid, readable JSON."""
        state_file = temp_data_dir / "bot_state.json"

        with patch('state.DATA_DIR', temp_data_dir):
            save_state(sample_bot_state, state_file)

        # Should be able to parse as JSON
        with open(state_file, 'r') as f:
            data = json.load(f)

        assert data['bot_id'] == "test_bot_001"
        assert data['total_trades'] == 10


class TestTradeLogging:
    """Test suite for trade logging functionality."""

    def test_log_trade_creates_file(self, temp_data_dir, sample_trade):
        """Test that log_trade creates the log file if it doesn't exist."""
        log_file = temp_data_dir / "trades.log"

        with patch('state.DATA_DIR', temp_data_dir):
            log_trade(sample_trade, log_file)

        assert log_file.exists()

    def test_log_trade_appends_records(self, temp_data_dir, sample_trade):
        """Test that log_trade appends multiple records."""
        log_file = temp_data_dir / "trades.log"

        with patch('state.DATA_DIR', temp_data_dir):
            log_trade(sample_trade, log_file)
            log_trade(sample_trade, log_file)

        lines = log_file.read_text().strip().split('\n')
        assert len(lines) == 2

    def test_log_trade_format(self, temp_data_dir, sample_trade):
        """Test that logged trade has correct JSON format."""
        log_file = temp_data_dir / "trades.log"

        with patch('state.DATA_DIR', temp_data_dir):
            log_trade(sample_trade, log_file)

        line = log_file.read_text().strip()
        entry = json.loads(line)

        assert 'logged_at' in entry
        assert 'trade' in entry
        assert entry['trade']['trade_id'] == "trade_001"
        assert entry['trade']['market_id'] == "market_123"
        assert entry['trade']['price'] == 0.65

    def test_load_trade_history_empty(self, temp_data_dir):
        """Test loading trade history from non-existent file."""
        log_file = temp_data_dir / "trades.log"

        trades = load_trade_history(log_file)

        assert trades == []

    def test_load_trade_history_multiple_trades(self, temp_data_dir, sample_trade):
        """Test loading multiple trades from history."""
        log_file = temp_data_dir / "trades.log"

        with patch('state.DATA_DIR', temp_data_dir):
            for i in range(5):
                log_trade(sample_trade, log_file)

        trades = load_trade_history(log_file)

        assert len(trades) == 5
        for trade in trades:
            assert 'logged_at' in trade
            assert 'trade' in trade

    def test_load_trade_history_with_limit(self, temp_data_dir, sample_trade):
        """Test loading trade history with limit parameter."""
        log_file = temp_data_dir / "trades.log"

        with patch('state.DATA_DIR', temp_data_dir):
            for i in range(10):
                log_trade(sample_trade, log_file)

        trades = load_trade_history(log_file, limit=3)

        assert len(trades) == 3


class TestMetricsLogging:
    """Test suite for metrics logging functionality."""

    def test_log_metrics_creates_file(self, temp_data_dir):
        """Test that log_metrics creates the log file."""
        log_file = temp_data_dir / "metrics.log"
        metrics = {"cycle": 1, "pnl": 50.0, "win_rate": 0.6}

        with patch('state.DATA_DIR', temp_data_dir):
            log_metrics(metrics, log_file)

        assert log_file.exists()

    def test_log_metrics_format(self, temp_data_dir):
        """Test that logged metrics have correct JSON format."""
        log_file = temp_data_dir / "metrics.log"
        metrics = {"cycle": 1, "pnl": 50.0, "win_rate": 0.6}

        with patch('state.DATA_DIR', temp_data_dir):
            log_metrics(metrics, log_file)

        line = log_file.read_text().strip()
        entry = json.loads(line)

        assert 'timestamp' in entry
        assert 'metrics' in entry
        assert entry['metrics']['cycle'] == 1
        assert entry['metrics']['pnl'] == 50.0

    def test_load_metrics_history(self, temp_data_dir):
        """Test loading metrics history."""
        log_file = temp_data_dir / "metrics.log"

        with patch('state.DATA_DIR', temp_data_dir):
            for i in range(5):
                metrics = {"cycle": i + 1, "pnl": i * 10.0}
                log_metrics(metrics, log_file)

        history = load_metrics_history(log_file)

        assert len(history) == 5
        assert history[0]['metrics']['cycle'] == 1
        assert history[4]['metrics']['cycle'] == 5

    def test_load_metrics_history_with_limit(self, temp_data_dir):
        """Test loading metrics history with limit."""
        log_file = temp_data_dir / "metrics.log"

        with patch('state.DATA_DIR', temp_data_dir):
            for i in range(10):
                metrics = {"cycle": i + 1}
                log_metrics(metrics, log_file)

        history = load_metrics_history(log_file, limit=3)

        assert len(history) == 3
        # Should get the last 3 entries
        assert history[0]['metrics']['cycle'] == 8
        assert history[2]['metrics']['cycle'] == 10


class TestLogRotation:
    """Test suite for log file rotation."""

    def test_rotate_log_if_needed_no_rotation_small_file(self, temp_data_dir):
        """Test that small files are not rotated."""
        log_file = temp_data_dir / "test.log"
        log_file.write_text("small content")

        _rotate_log_if_needed(log_file)

        # Original file should still exist, no backups
        assert log_file.exists()
        assert not (temp_data_dir / "test.log.1").exists()

    def test_rotate_log_if_needed_rotates_large_file(self, temp_data_dir):
        """Test that large files are rotated."""
        log_file = temp_data_dir / "test.log"

        # Create a file larger than MAX_LOG_SIZE
        large_content = "x" * (MAX_LOG_SIZE + 1000)
        log_file.write_text(large_content)

        _rotate_log_if_needed(log_file)

        # Original should be moved to .1
        backup_file = Path(f"{log_file}.1")
        assert backup_file.exists()
        assert backup_file.read_text() == large_content

    def test_rotate_log_multiple_backups(self, temp_data_dir):
        """Test that multiple rotations create numbered backups."""
        log_file = temp_data_dir / "test.log"

        # Rotate multiple times
        for i in range(3):
            content = f"content_{i}" * 10000  # Make it large
            content = content + ("x" * MAX_LOG_SIZE)
            log_file.write_text(content)
            _rotate_log_if_needed(log_file)

        # Should have .1, .2, .3 backups
        assert Path(f"{log_file}.1").exists()
        assert Path(f"{log_file}.2").exists()
        assert Path(f"{log_file}.3").exists()

    def test_rotate_log_respects_max_backups(self, temp_data_dir):
        """Test that rotation doesn't exceed MAX_LOG_BACKUPS."""
        log_file = temp_data_dir / "test.log"

        # Rotate more times than MAX_LOG_BACKUPS
        for i in range(MAX_LOG_BACKUPS + 3):
            content = "x" * (MAX_LOG_SIZE + 1000)
            log_file.write_text(content)
            _rotate_log_if_needed(log_file)

        # Count backup files
        backups = list(temp_data_dir.glob("test.log.*"))
        # Should not exceed MAX_LOG_BACKUPS
        assert len(backups) <= MAX_LOG_BACKUPS


class TestCrashRecovery:
    """Test suite for crash recovery functionality."""

    def test_clean_temp_files_removes_tmp_files(self, temp_data_dir):
        """Test that clean_temp_files removes .tmp files."""
        temp_file1 = temp_data_dir / "state.json.tmp"
        temp_file2 = temp_data_dir / "trades.log.tmp"

        temp_file1.write_text("temp data 1")
        temp_file2.write_text("temp data 2")

        with patch('state.DATA_DIR', temp_data_dir):
            clean_temp_files()

        assert not temp_file1.exists()
        assert not temp_file2.exists()

    def test_clean_temp_files_preserves_normal_files(self, temp_data_dir):
        """Test that clean_temp_files doesn't remove normal files."""
        normal_file = temp_data_dir / "state.json"
        temp_file = temp_data_dir / "state.json.tmp"

        normal_file.write_text("normal data")
        temp_file.write_text("temp data")

        with patch('state.DATA_DIR', temp_data_dir):
            clean_temp_files()

        assert normal_file.exists()
        assert not temp_file.exists()

    def test_clean_temp_files_handles_missing_directory(self, temp_data_dir):
        """Test that clean_temp_files works when directory doesn't exist."""
        nonexistent_dir = temp_data_dir / "nonexistent"

        with patch('state.DATA_DIR', nonexistent_dir):
            # Should not raise an error
            clean_temp_files()
            # Directory should be created
            assert nonexistent_dir.exists()


class TestStateSummary:
    """Test suite for state summary functionality."""

    def test_get_state_summary_calculates_win_rate(self, sample_bot_state):
        """Test that state summary calculates win rate correctly."""
        summary = get_state_summary(sample_bot_state)

        assert summary['total_trades'] == 10
        assert summary['winning_trades'] == 6
        assert summary['win_rate_percent'] == 60.0

    def test_get_state_summary_handles_zero_trades(self):
        """Test that state summary handles zero trades without error."""
        state = BotState(
            bot_id="test_bot",
            strategy_name="test",
            max_position_size=Decimal("100"),
            max_total_exposure=Decimal("500"),
            risk_per_trade=Decimal("10"),
            total_trades=0,
            winning_trades=0
        )

        summary = get_state_summary(state)

        assert summary['win_rate_percent'] == 0.0

    def test_get_state_summary_includes_key_metrics(self, sample_bot_state):
        """Test that state summary includes all key metrics."""
        summary = get_state_summary(sample_bot_state)

        assert 'bot_id' in summary
        assert 'status' in summary
        assert 'total_trades' in summary
        assert 'winning_trades' in summary
        assert 'win_rate_percent' in summary
        assert 'total_pnl' in summary
        assert 'current_exposure' in summary
        assert 'active_markets_count' in summary
        assert 'last_heartbeat' in summary

    def test_get_state_summary_formats_correctly(self, sample_bot_state):
        """Test that state summary formats data correctly."""
        summary = get_state_summary(sample_bot_state)

        assert summary['total_pnl'] == 250.50  # Float conversion
        assert summary['current_exposure'] == 1500.00
        assert summary['active_markets_count'] == 2
        assert summary['status'] == 'running'


class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_state_workflow(self, temp_data_dir, sample_bot_state, sample_trade):
        """Test complete workflow: save state, log trades, load everything."""
        state_file = temp_data_dir / "bot_state.json"
        trades_log = temp_data_dir / "trades.log"
        metrics_log = temp_data_dir / "metrics.log"

        with patch('state.DATA_DIR', temp_data_dir):
            # Save initial state
            save_state(sample_bot_state, state_file)

            # Log some trades
            for i in range(3):
                log_trade(sample_trade, trades_log)

            # Log some metrics
            for i in range(3):
                log_metrics({"cycle": i + 1, "pnl": i * 10.0}, metrics_log)

            # Load everything back
            loaded_state = load_state(state_file)
            trade_history = load_trade_history(trades_log)
            metrics_history = load_metrics_history(metrics_log)

        assert loaded_state.bot_id == sample_bot_state.bot_id
        assert len(trade_history) == 3
        assert len(metrics_history) == 3

    def test_simulated_crash_recovery(self, temp_data_dir, sample_bot_state):
        """Test recovery from simulated crash during write."""
        state_file = temp_data_dir / "bot_state.json"

        # Save initial state
        with patch('state.DATA_DIR', temp_data_dir):
            save_state(sample_bot_state, state_file)
            original_content = state_file.read_text()

            # Create a temp file (simulating interrupted write)
            temp_file = state_file.with_suffix(state_file.suffix + ".tmp")
            temp_file.write_text("corrupted partial data")

            # Run cleanup
            clean_temp_files()

            # Temp file should be gone
            assert not temp_file.exists()

            # Original state file should be intact
            assert state_file.read_text() == original_content

            # Should still be able to load state
            loaded_state = load_state(state_file)
            assert loaded_state.bot_id == sample_bot_state.bot_id

    def test_concurrent_operations(self, temp_data_dir, sample_trade):
        """Test that multiple operations work correctly in sequence."""
        trades_log = temp_data_dir / "trades.log"

        with patch('state.DATA_DIR', temp_data_dir):
            # Simulate rapid logging
            for i in range(100):
                log_trade(sample_trade, trades_log)

            # Load and verify
            history = load_trade_history(trades_log)
            assert len(history) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
