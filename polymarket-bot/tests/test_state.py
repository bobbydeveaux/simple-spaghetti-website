"""
Tests for state persistence and logging system.
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from state import StateManager, create_state_manager, recover_state
from models import BotState, Trade, OrderSide, OrderType, TradeStatus, OutcomeType, BotStatus


class TestStateManager:
    """Test StateManager functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    @pytest.fixture
    def state_manager(self, temp_dir):
        """Create a StateManager instance for testing."""
        return StateManager(state_dir=temp_dir)

    @pytest.fixture
    def sample_bot_state(self):
        """Create a sample BotState for testing."""
        return BotState(
            bot_id="test_bot_001",
            strategy_name="test_strategy",
            max_position_size=Decimal("1000.00"),
            max_total_exposure=Decimal("5000.00"),
            risk_per_trade=Decimal("100.00")
        )

    @pytest.fixture
    def sample_trade(self):
        """Create a sample Trade for testing."""
        return Trade(
            trade_id="trade_001",
            market_id="market_123",
            order_id="order_456",
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            outcome=OutcomeType.YES,
            price=Decimal("0.65"),
            quantity=Decimal("100")
        )

    def test_initialization(self, temp_dir):
        """Test StateManager initialization."""
        state_manager = StateManager(state_dir=temp_dir)

        assert state_manager.state_dir == Path(temp_dir)
        assert state_manager.state_file == Path(temp_dir) / "bot_state.json"
        assert state_manager.trades_log == Path(temp_dir) / "trades.log"
        assert Path(temp_dir).exists()

    def test_save_state(self, state_manager, sample_bot_state):
        """Test saving bot state to disk."""
        state_manager.save_state(sample_bot_state)

        assert state_manager.state_file.exists()

        # Verify file contents
        with open(state_manager.state_file, 'r') as f:
            saved_data = json.load(f)

        assert saved_data['bot_id'] == "test_bot_001"
        assert saved_data['strategy_name'] == "test_strategy"
        assert saved_data['max_position_size'] == 1000.00

    def test_load_state(self, state_manager, sample_bot_state):
        """Test loading bot state from disk."""
        # Save state first
        state_manager.save_state(sample_bot_state)

        # Load it back
        loaded_state = state_manager.load_state()

        assert loaded_state is not None
        assert loaded_state['bot_id'] == "test_bot_001"
        assert loaded_state['strategy_name'] == "test_strategy"

    def test_load_state_nonexistent(self, state_manager):
        """Test loading state when file doesn't exist."""
        loaded_state = state_manager.load_state()
        assert loaded_state is None

    def test_load_state_corrupted(self, state_manager):
        """Test loading corrupted state file."""
        # Write invalid JSON to state file
        with open(state_manager.state_file, 'w') as f:
            f.write("invalid json{{{")

        with pytest.raises(ValueError, match="Corrupted state file"):
            state_manager.load_state()

    def test_atomic_write(self, state_manager, sample_bot_state):
        """Test atomic write operation prevents corruption."""
        # Save initial state
        state_manager.save_state(sample_bot_state)

        # Modify and save again
        sample_bot_state.total_trades = 10
        state_manager.save_state(sample_bot_state)

        # Verify no temporary file left behind
        temp_file = state_manager.state_file.with_suffix('.tmp')
        assert not temp_file.exists()

        # Verify state is correct
        loaded_state = state_manager.load_state()
        assert loaded_state['total_trades'] == 10

    def test_validate_state_valid(self, state_manager):
        """Test state validation with valid data."""
        valid_state = {
            'bot_id': 'bot_001',
            'status': 'running',
            'strategy_name': 'test',
            'max_position_size': 1000.0,
            'max_total_exposure': 5000.0,
            'risk_per_trade': 100.0
        }

        assert state_manager.validate_state(valid_state) is True

    def test_validate_state_invalid(self, state_manager):
        """Test state validation with invalid data."""
        invalid_state = {
            'bot_id': 'bot_001',
            'status': 'running'
            # Missing required fields
        }

        assert state_manager.validate_state(invalid_state) is False

    def test_log_trade(self, state_manager, sample_trade):
        """Test logging a trade to file."""
        state_manager.log_trade(sample_trade)

        assert state_manager.trades_log.exists()

        # Verify log contents
        with open(state_manager.trades_log, 'r') as f:
            log_line = f.readline()
            log_entry = json.loads(log_line)

        assert 'timestamp' in log_entry
        assert log_entry['trade']['trade_id'] == 'trade_001'
        assert log_entry['trade']['market_id'] == 'market_123'

    def test_log_multiple_trades(self, state_manager, sample_trade):
        """Test logging multiple trades."""
        # Log multiple trades
        for i in range(3):
            sample_trade.trade_id = f"trade_{i:03d}"
            state_manager.log_trade(sample_trade)

        # Load and verify all trades
        trades = state_manager.load_trades()
        assert len(trades) == 3
        assert trades[0]['trade']['trade_id'] == 'trade_000'
        assert trades[2]['trade']['trade_id'] == 'trade_002'

    def test_load_trades_empty(self, state_manager):
        """Test loading trades when file doesn't exist."""
        trades = state_manager.load_trades()
        assert trades == []

    def test_load_trades_corrupted(self, state_manager):
        """Test loading corrupted trades log."""
        # Write invalid JSON
        with open(state_manager.trades_log, 'w') as f:
            f.write("invalid json{{{")

        with pytest.raises(ValueError, match="Corrupted trades log"):
            state_manager.load_trades()

    def test_update_metrics_win(self, state_manager):
        """Test updating metrics for winning trade."""
        state_manager.update_metrics(
            trade_result="win",
            pnl=Decimal("50.00"),
            current_equity=Decimal("1050.00")
        )

        metrics = state_manager.get_metrics()
        assert metrics['total_trades'] == 1
        assert metrics['winning_trades'] == 1
        assert metrics['losing_trades'] == 0
        assert metrics['win_streak'] == 1
        assert metrics['loss_streak'] == 0

    def test_update_metrics_loss(self, state_manager):
        """Test updating metrics for losing trade."""
        state_manager.update_metrics(
            trade_result="loss",
            pnl=Decimal("-30.00"),
            current_equity=Decimal("970.00")
        )

        metrics = state_manager.get_metrics()
        assert metrics['total_trades'] == 1
        assert metrics['winning_trades'] == 0
        assert metrics['losing_trades'] == 1
        assert metrics['win_streak'] == 0
        assert metrics['loss_streak'] == 1

    def test_update_metrics_streak(self, state_manager):
        """Test win/loss streak tracking."""
        # Three wins
        for _ in range(3):
            state_manager.update_metrics("win", Decimal("50"), Decimal("1050"))

        metrics = state_manager.get_metrics()
        assert metrics['win_streak'] == 3

        # One loss (resets win streak)
        state_manager.update_metrics("loss", Decimal("-30"), Decimal("1020"))

        metrics = state_manager.get_metrics()
        assert metrics['win_streak'] == 0
        assert metrics['loss_streak'] == 1

    def test_update_metrics_drawdown(self, state_manager):
        """Test drawdown calculation."""
        # Initial high equity
        state_manager.update_metrics("win", Decimal("100"), Decimal("1100"))

        # Drop in equity
        state_manager.update_metrics("loss", Decimal("-200"), Decimal("900"))

        metrics = state_manager.get_metrics()
        # Drawdown should be (1100 - 900) / 1100 = 0.1818...
        assert metrics['max_drawdown'] > 0.18
        assert metrics['max_drawdown'] < 0.19

    def test_get_metrics(self, state_manager):
        """Test getting current metrics."""
        metrics = state_manager.get_metrics()

        assert 'win_streak' in metrics
        assert 'loss_streak' in metrics
        assert 'max_drawdown' in metrics
        assert 'peak_equity' in metrics
        assert 'total_trades' in metrics
        assert 'winning_trades' in metrics
        assert 'losing_trades' in metrics
        assert 'win_rate' in metrics

    def test_calculate_win_rate(self, state_manager):
        """Test win rate calculation."""
        # No trades
        assert state_manager._calculate_win_rate() == 0.0

        # 3 wins, 2 losses
        for _ in range(3):
            state_manager.update_metrics("win", Decimal("50"), Decimal("1050"))
        for _ in range(2):
            state_manager.update_metrics("loss", Decimal("-30"), Decimal("1020"))

        win_rate = state_manager._calculate_win_rate()
        assert win_rate == 60.0  # 3/5 * 100

    def test_reset_metrics(self, state_manager):
        """Test resetting metrics."""
        # Add some data
        state_manager.update_metrics("win", Decimal("50"), Decimal("1050"))
        state_manager.update_metrics("win", Decimal("50"), Decimal("1100"))

        # Reset
        state_manager.reset_metrics()

        metrics = state_manager.get_metrics()
        assert metrics['total_trades'] == 0
        assert metrics['winning_trades'] == 0
        assert metrics['win_streak'] == 0

    def test_save_and_load_metrics(self, state_manager):
        """Test saving and loading metrics."""
        # Update metrics
        state_manager.update_metrics("win", Decimal("50"), Decimal("1050"))
        state_manager.update_metrics("loss", Decimal("-30"), Decimal("1020"))

        # Save
        state_manager.save_metrics()

        # Create new manager and load
        new_manager = StateManager(state_dir=str(state_manager.state_dir))
        new_manager.load_metrics()

        metrics = new_manager.get_metrics()
        assert metrics['total_trades'] == 2
        assert metrics['winning_trades'] == 1
        assert metrics['losing_trades'] == 1


class TestHelperFunctions:
    """Test helper functions."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_create_state_manager(self, temp_dir):
        """Test create_state_manager helper."""
        manager = create_state_manager(state_dir=temp_dir)

        assert isinstance(manager, StateManager)
        assert manager.state_dir == Path(temp_dir)

    def test_recover_state_success(self, temp_dir):
        """Test successful state recovery."""
        manager = create_state_manager(state_dir=temp_dir)

        # Save a state
        bot_state = BotState(
            bot_id="recovery_test",
            strategy_name="test_strategy",
            max_position_size=Decimal("1000.00"),
            max_total_exposure=Decimal("5000.00"),
            risk_per_trade=Decimal("100.00")
        )
        manager.save_state(bot_state)

        # Recover it
        recovered = recover_state(manager)

        assert recovered is not None
        assert recovered['bot_id'] == "recovery_test"

    def test_recover_state_no_file(self, temp_dir):
        """Test state recovery when file doesn't exist."""
        manager = create_state_manager(state_dir=temp_dir)

        recovered = recover_state(manager)
        assert recovered is None

    def test_recover_state_invalid(self, temp_dir):
        """Test state recovery with invalid state."""
        manager = create_state_manager(state_dir=temp_dir)

        # Write invalid state
        with open(manager.state_file, 'w') as f:
            json.dump({'incomplete': 'data'}, f)

        recovered = recover_state(manager)
        assert recovered is None


class TestIntegration:
    """Integration tests for state management."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_full_workflow(self, temp_dir):
        """Test complete state management workflow."""
        manager = StateManager(state_dir=temp_dir)

        # Create and save bot state
        bot_state = BotState(
            bot_id="workflow_test",
            strategy_name="test_strategy",
            max_position_size=Decimal("1000.00"),
            max_total_exposure=Decimal("5000.00"),
            risk_per_trade=Decimal("100.00")
        )
        manager.save_state(bot_state)

        # Create and log multiple trades
        for i in range(5):
            trade = Trade(
                trade_id=f"trade_{i:03d}",
                market_id="market_123",
                order_id=f"order_{i:03d}",
                side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
                order_type=OrderType.LIMIT,
                outcome=OutcomeType.YES,
                price=Decimal("0.65"),
                quantity=Decimal("100")
            )
            manager.log_trade(trade)

            # Update metrics
            result = "win" if i % 2 == 0 else "loss"
            manager.update_metrics(result, Decimal("50"), Decimal("1050"))

        # Save metrics
        manager.save_metrics()

        # Verify everything
        loaded_state = manager.load_state()
        assert loaded_state['bot_id'] == "workflow_test"

        loaded_trades = manager.load_trades()
        assert len(loaded_trades) == 5

        metrics = manager.get_metrics()
        assert metrics['total_trades'] == 5
        assert metrics['winning_trades'] == 3  # trades 0, 2, 4
        assert metrics['losing_trades'] == 2   # trades 1, 3

    def test_crash_recovery_scenario(self, temp_dir):
        """Test crash recovery scenario."""
        # Initial manager saves state
        manager1 = StateManager(state_dir=temp_dir)
        bot_state = BotState(
            bot_id="crash_test",
            strategy_name="test_strategy",
            max_position_size=Decimal("1000.00"),
            max_total_exposure=Decimal("5000.00"),
            risk_per_trade=Decimal("100.00"),
            total_trades=10
        )
        manager1.save_state(bot_state)

        # Simulate crash - create new manager
        manager2 = StateManager(state_dir=temp_dir)

        # Recover state
        recovered = recover_state(manager2)

        assert recovered is not None
        assert recovered['bot_id'] == "crash_test"
        assert recovered['total_trades'] == 10
