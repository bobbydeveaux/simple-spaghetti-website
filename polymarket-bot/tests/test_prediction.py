"""
Unit tests for the prediction engine.

This module provides comprehensive test coverage for the prediction engine
including signal generation, indicator calculations, confidence scoring,
and edge cases.
"""

import pytest
import sys
from pathlib import Path
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add parent directory to path to allow imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from prediction import (
    PredictionEngine,
    PredictionError,
    generate_signal_from_market_data,
    _validate_signal_conditions
)
from models import PredictionSignal, SignalType
from config import Config


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    config = Mock(spec=Config)
    config.rsi_period = 14
    config.rsi_oversold_threshold = 30.0
    config.rsi_overbought_threshold = 70.0
    config.macd_fast_period = 12
    config.macd_slow_period = 26
    config.macd_signal_period = 9
    config.order_book_bullish_threshold = 1.1
    config.order_book_bearish_threshold = 0.9
    config.prediction_confidence_score = 0.75
    return config


@pytest.fixture
def prediction_engine(mock_config):
    """Create a prediction engine instance with mock config."""
    return PredictionEngine(config=mock_config)


@pytest.fixture
def sample_prices():
    """Generate sample price data for testing."""
    # Generate 50 price points with some variation
    base_price = 45000.0
    prices = []
    for i in range(50):
        price = base_price + (i * 10) + ((-1) ** i * 50)
        prices.append(price)
    return prices


class TestPredictionEngine:
    """Test suite for PredictionEngine class."""

    def test_initialization(self, mock_config):
        """Test that prediction engine initializes correctly."""
        engine = PredictionEngine(config=mock_config)
        assert engine.config == mock_config
        assert engine.config.rsi_period == 14
        assert engine.config.rsi_oversold_threshold == 30.0
        assert engine.config.rsi_overbought_threshold == 70.0

    def test_initialization_without_config(self):
        """Test initialization without explicit config (uses get_config)."""
        with patch('prediction.get_config') as mock_get_config:
            mock_cfg = Mock(spec=Config)
            mock_cfg.rsi_period = 14
            mock_cfg.rsi_oversold_threshold = 30.0
            mock_cfg.rsi_overbought_threshold = 70.0
            mock_cfg.macd_fast_period = 12
            mock_cfg.macd_slow_period = 26
            mock_cfg.macd_signal_period = 9
            mock_get_config.return_value = mock_cfg

            engine = PredictionEngine()
            assert engine.config == mock_cfg

    def test_validate_price_data_sufficient(self, prediction_engine, sample_prices):
        """Test that validation passes with sufficient price data."""
        assert prediction_engine.validate_price_data(sample_prices) is True

    def test_validate_price_data_insufficient(self, prediction_engine):
        """Test that validation fails with insufficient price data."""
        insufficient_prices = [45000.0, 45100.0]
        assert prediction_engine.validate_price_data(insufficient_prices) is False

    def test_validate_price_data_negative_prices(self, prediction_engine, sample_prices):
        """Test that validation fails with negative prices."""
        invalid_prices = sample_prices.copy()
        invalid_prices[10] = -100.0
        assert prediction_engine.validate_price_data(invalid_prices) is False

    def test_validate_price_data_zero_prices(self, prediction_engine, sample_prices):
        """Test that validation fails with zero prices."""
        invalid_prices = sample_prices.copy()
        invalid_prices[10] = 0.0
        assert prediction_engine.validate_price_data(invalid_prices) is False


class TestSignalGeneration:
    """Test suite for signal generation logic."""

    @patch('prediction.calculate_rsi')
    @patch('prediction.calculate_macd')
    @patch('prediction.get_order_book_imbalance')
    def test_generate_up_signal(
        self,
        mock_order_book,
        mock_macd,
        mock_rsi,
        prediction_engine,
        sample_prices
    ):
        """Test generation of UP signal with correct conditions."""
        # Set up conditions for UP signal
        mock_rsi.return_value = 28.0  # Oversold
        mock_macd.return_value = (150.0, 145.0)  # MACD > signal (bullish)
        mock_order_book.return_value = 1.2  # Strong buying pressure

        signal = prediction_engine.generate_signal(sample_prices, btc_price=45000.0)

        assert signal.signal == SignalType.UP
        assert signal.confidence == Decimal('0.75')
        assert signal.rsi == Decimal('28.0')
        assert signal.macd_line == Decimal('150.0')
        assert signal.macd_signal == Decimal('145.0')
        assert signal.order_book_imbalance == Decimal('1.2')
        assert signal.btc_price == Decimal('45000.0')
        assert "oversold" in signal.reasoning.lower()
        assert "bullish" in signal.reasoning.lower()
        assert signal.is_actionable() is True
        assert signal.get_direction() == "UP"

    @patch('prediction.calculate_rsi')
    @patch('prediction.calculate_macd')
    @patch('prediction.get_order_book_imbalance')
    def test_generate_down_signal(
        self,
        mock_order_book,
        mock_macd,
        mock_rsi,
        prediction_engine,
        sample_prices
    ):
        """Test generation of DOWN signal with correct conditions."""
        # Set up conditions for DOWN signal
        mock_rsi.return_value = 75.0  # Overbought
        mock_macd.return_value = (140.0, 145.0)  # MACD < signal (bearish)
        mock_order_book.return_value = 0.8  # Strong selling pressure

        signal = prediction_engine.generate_signal(sample_prices, btc_price=45000.0)

        assert signal.signal == SignalType.DOWN
        assert signal.confidence == Decimal('0.75')
        assert signal.rsi == Decimal('75.0')
        assert signal.macd_line == Decimal('140.0')
        assert signal.macd_signal == Decimal('145.0')
        assert signal.order_book_imbalance == Decimal('0.8')
        assert "overbought" in signal.reasoning.lower()
        assert "bearish" in signal.reasoning.lower()
        assert signal.is_actionable() is True
        assert signal.get_direction() == "DOWN"

    @patch('prediction.calculate_rsi')
    @patch('prediction.calculate_macd')
    @patch('prediction.get_order_book_imbalance')
    def test_generate_skip_signal(
        self,
        mock_order_book,
        mock_macd,
        mock_rsi,
        prediction_engine,
        sample_prices
    ):
        """Test generation of SKIP signal when conditions not met."""
        # Set up conditions that don't meet UP or DOWN criteria
        mock_rsi.return_value = 50.0  # Neutral
        mock_macd.return_value = (145.0, 145.0)  # MACD = signal (neutral)
        mock_order_book.return_value = 1.0  # Neutral

        signal = prediction_engine.generate_signal(sample_prices, btc_price=45000.0)

        assert signal.signal == SignalType.SKIP
        assert signal.confidence == Decimal('0.0')
        assert signal.rsi == Decimal('50.0')
        assert "no clear signal" in signal.reasoning.lower()
        assert signal.is_actionable() is False
        assert signal.get_direction() is None

    @patch('prediction.calculate_rsi')
    @patch('prediction.calculate_macd')
    @patch('prediction.get_order_book_imbalance')
    def test_generate_signal_without_btc_price(
        self,
        mock_order_book,
        mock_macd,
        mock_rsi,
        prediction_engine,
        sample_prices
    ):
        """Test signal generation without BTC price context."""
        mock_rsi.return_value = 28.0
        mock_macd.return_value = (150.0, 145.0)
        mock_order_book.return_value = 1.2

        signal = prediction_engine.generate_signal(sample_prices)

        assert signal.signal == SignalType.UP
        assert signal.btc_price is None

    @patch('prediction.calculate_rsi')
    def test_generate_signal_rsi_error(
        self,
        mock_rsi,
        prediction_engine,
        sample_prices
    ):
        """Test error handling when RSI calculation fails."""
        mock_rsi.side_effect = ValueError("Insufficient data")

        with pytest.raises(PredictionError, match="Failed to generate signal"):
            prediction_engine.generate_signal(sample_prices)

    @patch('prediction.calculate_rsi')
    @patch('prediction.calculate_macd')
    def test_generate_signal_macd_error(
        self,
        mock_macd,
        mock_rsi,
        prediction_engine,
        sample_prices
    ):
        """Test error handling when MACD calculation fails."""
        mock_rsi.return_value = 50.0
        mock_macd.side_effect = ValueError("Insufficient data")

        with pytest.raises(PredictionError, match="Failed to generate signal"):
            prediction_engine.generate_signal(sample_prices)

    @patch('prediction.calculate_rsi')
    @patch('prediction.calculate_macd')
    @patch('prediction.get_order_book_imbalance')
    def test_generate_signal_order_book_error(
        self,
        mock_order_book,
        mock_macd,
        mock_rsi,
        prediction_engine,
        sample_prices
    ):
        """Test error handling when order book fetch fails."""
        mock_rsi.return_value = 50.0
        mock_macd.return_value = (145.0, 145.0)
        mock_order_book.side_effect = ConnectionError("API unavailable")

        with pytest.raises(PredictionError, match="Failed to generate signal"):
            prediction_engine.generate_signal(sample_prices)


class TestConditionEvaluation:
    """Test suite for condition evaluation logic."""

    def test_evaluate_up_conditions(self, prediction_engine):
        """Test UP signal conditions evaluation."""
        signal, confidence, reasoning = prediction_engine._evaluate_conditions(
            rsi=25.0,
            macd_line=150.0,
            macd_signal=145.0,
            order_book_imbalance=1.15
        )

        assert signal == SignalType.UP
        assert confidence == 0.75
        assert "oversold" in reasoning.lower()

    def test_evaluate_down_conditions(self, prediction_engine):
        """Test DOWN signal conditions evaluation."""
        signal, confidence, reasoning = prediction_engine._evaluate_conditions(
            rsi=75.0,
            macd_line=140.0,
            macd_signal=145.0,
            order_book_imbalance=0.85
        )

        assert signal == SignalType.DOWN
        assert confidence == 0.75
        assert "overbought" in reasoning.lower()

    def test_evaluate_skip_conditions_neutral_rsi(self, prediction_engine):
        """Test SKIP signal when RSI is neutral."""
        signal, confidence, reasoning = prediction_engine._evaluate_conditions(
            rsi=50.0,
            macd_line=150.0,
            macd_signal=145.0,
            order_book_imbalance=1.15
        )

        assert signal == SignalType.SKIP
        assert confidence == 0.0

    def test_evaluate_skip_conditions_conflicting_macd(self, prediction_engine):
        """Test SKIP signal when MACD conflicts with RSI."""
        signal, confidence, reasoning = prediction_engine._evaluate_conditions(
            rsi=25.0,
            macd_line=140.0,
            macd_signal=145.0,  # Bearish MACD with oversold RSI
            order_book_imbalance=1.15
        )

        assert signal == SignalType.SKIP
        assert confidence == 0.0

    def test_evaluate_skip_conditions_conflicting_order_book(self, prediction_engine):
        """Test SKIP signal when order book conflicts."""
        signal, confidence, reasoning = prediction_engine._evaluate_conditions(
            rsi=25.0,
            macd_line=150.0,
            macd_signal=145.0,
            order_book_imbalance=0.95  # Not enough buying pressure
        )

        assert signal == SignalType.SKIP
        assert confidence == 0.0

    def test_evaluate_boundary_up_conditions(self, prediction_engine):
        """Test UP signal at boundary conditions."""
        # Just below oversold threshold
        signal, confidence, _ = prediction_engine._evaluate_conditions(
            rsi=29.9,
            macd_line=145.1,
            macd_signal=145.0,
            order_book_imbalance=1.11
        )

        assert signal == SignalType.UP

    def test_evaluate_boundary_down_conditions(self, prediction_engine):
        """Test DOWN signal at boundary conditions."""
        # Just above overbought threshold
        signal, confidence, _ = prediction_engine._evaluate_conditions(
            rsi=70.1,
            macd_line=144.9,
            macd_signal=145.0,
            order_book_imbalance=0.89
        )

        assert signal == SignalType.DOWN

    def test_evaluate_exact_threshold_skip(self, prediction_engine):
        """Test SKIP signal when exactly at threshold (not meeting strict conditions)."""
        # Exactly at oversold threshold (not less than)
        signal, confidence, _ = prediction_engine._evaluate_conditions(
            rsi=30.0,
            macd_line=150.0,
            macd_signal=145.0,
            order_book_imbalance=1.15
        )

        assert signal == SignalType.SKIP


class TestConvenienceFunctions:
    """Test suite for convenience functions."""

    @patch('prediction.PredictionEngine')
    def test_generate_signal_from_market_data(self, mock_engine_class, sample_prices, mock_config):
        """Test convenience function for signal generation."""
        mock_engine = Mock()
        mock_signal = Mock(spec=PredictionSignal)
        mock_engine.generate_signal.return_value = mock_signal
        mock_engine_class.return_value = mock_engine

        result = generate_signal_from_market_data(
            prices=sample_prices,
            btc_price=45000.0,
            config=mock_config
        )

        assert result == mock_signal
        mock_engine_class.assert_called_once_with(config=mock_config)
        mock_engine.generate_signal.assert_called_once_with(
            prices=sample_prices,
            btc_price=45000.0
        )

    @patch('prediction.get_config')
    def test__validate_signal_conditions_up(self, mock_get_config, mock_config):
        """Test validate_signal_conditions for UP signal."""
        mock_get_config.return_value = mock_config

        signal = _validate_signal_conditions(
            rsi=25.0,
            macd_line=150.0,
            macd_signal=145.0,
            order_book_imbalance=1.15,
            config=mock_config
        )

        assert signal == SignalType.UP

    @patch('prediction.get_config')
    def test__validate_signal_conditions_down(self, mock_get_config, mock_config):
        """Test validate_signal_conditions for DOWN signal."""
        mock_get_config.return_value = mock_config

        signal = _validate_signal_conditions(
            rsi=75.0,
            macd_line=140.0,
            macd_signal=145.0,
            order_book_imbalance=0.85,
            config=mock_config
        )

        assert signal == SignalType.DOWN

    @patch('prediction.get_config')
    def test__validate_signal_conditions_skip(self, mock_get_config, mock_config):
        """Test validate_signal_conditions for SKIP signal."""
        mock_get_config.return_value = mock_config

        signal = _validate_signal_conditions(
            rsi=50.0,
            macd_line=145.0,
            macd_signal=145.0,
            order_book_imbalance=1.0,
            config=mock_config
        )

        assert signal == SignalType.SKIP


class TestPredictionSignalModel:
    """Test suite for PredictionSignal model methods."""

    def test_prediction_signal_to_dict(self):
        """Test PredictionSignal serialization to dictionary."""
        signal = PredictionSignal(
            signal=SignalType.UP,
            confidence=Decimal('0.75'),
            rsi=Decimal('28.5'),
            macd_line=Decimal('150.23'),
            macd_signal=Decimal('145.10'),
            order_book_imbalance=Decimal('1.15'),
            btc_price=Decimal('45678.90'),
            reasoning="Test reasoning"
        )

        signal_dict = signal.to_dict()

        assert signal_dict['signal'] == 'up'
        assert signal_dict['confidence'] == 0.75
        assert signal_dict['rsi'] == 28.5
        assert signal_dict['macd_line'] == 150.23
        assert signal_dict['macd_signal'] == 145.10
        assert signal_dict['order_book_imbalance'] == 1.15
        assert signal_dict['btc_price'] == 45678.90
        assert signal_dict['reasoning'] == "Test reasoning"

    def test_prediction_signal_is_actionable_up(self):
        """Test is_actionable returns True for UP signal."""
        signal = PredictionSignal(
            signal=SignalType.UP,
            confidence=Decimal('0.75')
        )
        assert signal.is_actionable() is True

    def test_prediction_signal_is_actionable_down(self):
        """Test is_actionable returns True for DOWN signal."""
        signal = PredictionSignal(
            signal=SignalType.DOWN,
            confidence=Decimal('0.75')
        )
        assert signal.is_actionable() is True

    def test_prediction_signal_is_actionable_skip(self):
        """Test is_actionable returns False for SKIP signal."""
        signal = PredictionSignal(
            signal=SignalType.SKIP,
            confidence=Decimal('0.0')
        )
        assert signal.is_actionable() is False

    def test_prediction_signal_get_direction_up(self):
        """Test get_direction returns UP for UP signal."""
        signal = PredictionSignal(
            signal=SignalType.UP,
            confidence=Decimal('0.75')
        )
        assert signal.get_direction() == "UP"

    def test_prediction_signal_get_direction_down(self):
        """Test get_direction returns DOWN for DOWN signal."""
        signal = PredictionSignal(
            signal=SignalType.DOWN,
            confidence=Decimal('0.75')
        )
        assert signal.get_direction() == "DOWN"

    def test_prediction_signal_get_direction_skip(self):
        """Test get_direction returns None for SKIP signal."""
        signal = PredictionSignal(
            signal=SignalType.SKIP,
            confidence=Decimal('0.0')
        )
        assert signal.get_direction() is None


class TestEdgeCases:
    """Test suite for edge cases and error conditions."""

    @patch('prediction.calculate_rsi')
    @patch('prediction.calculate_macd')
    @patch('prediction.get_order_book_imbalance')
    def test_extreme_rsi_values(
        self,
        mock_order_book,
        mock_macd,
        mock_rsi,
        prediction_engine,
        sample_prices
    ):
        """Test handling of extreme RSI values."""
        mock_rsi.return_value = 5.0  # Very oversold
        mock_macd.return_value = (150.0, 145.0)
        mock_order_book.return_value = 1.5

        signal = prediction_engine.generate_signal(sample_prices)
        assert signal.signal == SignalType.UP

    @patch('prediction.calculate_rsi')
    @patch('prediction.calculate_macd')
    @patch('prediction.get_order_book_imbalance')
    def test_extreme_order_book_imbalance(
        self,
        mock_order_book,
        mock_macd,
        mock_rsi,
        prediction_engine,
        sample_prices
    ):
        """Test handling of extreme order book imbalance."""
        mock_rsi.return_value = 25.0
        mock_macd.return_value = (150.0, 145.0)
        mock_order_book.return_value = 5.0  # Very high buying pressure

        signal = prediction_engine.generate_signal(sample_prices)
        assert signal.signal == SignalType.UP

    @patch('prediction.calculate_rsi')
    @patch('prediction.calculate_macd')
    @patch('prediction.get_order_book_imbalance')
    def test_macd_zero_values(
        self,
        mock_order_book,
        mock_macd,
        mock_rsi,
        prediction_engine,
        sample_prices
    ):
        """Test handling when MACD values are zero."""
        mock_rsi.return_value = 25.0
        mock_macd.return_value = (0.0, 0.0)
        mock_order_book.return_value = 1.2

        signal = prediction_engine.generate_signal(sample_prices)
        # With MACD at 0,0 (neither > nor <), should be SKIP
        assert signal.signal == SignalType.SKIP

    @patch('prediction.calculate_rsi')
    @patch('prediction.calculate_macd')
    @patch('prediction.get_order_book_imbalance')
    def test_conflicting_indicators(
        self,
        mock_order_book,
        mock_macd,
        mock_rsi,
        prediction_engine,
        sample_prices
    ):
        """Test handling when indicators give conflicting signals."""
        # RSI says oversold, MACD says bearish, order book says bullish
        mock_rsi.return_value = 25.0  # Oversold
        mock_macd.return_value = (140.0, 145.0)  # Bearish
        mock_order_book.return_value = 1.2  # Bullish

        signal = prediction_engine.generate_signal(sample_prices)
        assert signal.signal == SignalType.SKIP


class TestIntegration:
    """Integration tests for the full prediction pipeline."""

    @patch('prediction.get_order_book_imbalance')
    def test_full_prediction_pipeline_real_calculations(
        self,
        mock_order_book,
        prediction_engine
    ):
        """Test full prediction pipeline with real RSI/MACD calculations."""
        # Generate realistic price data for an uptrend
        prices = []
        base = 45000.0
        for i in range(50):
            # Simulate oversold condition with slight uptrend
            price = base - 500 + (i * 5)
            prices.append(price)

        mock_order_book.return_value = 1.2

        # This should generate a signal (likely UP or SKIP depending on actual RSI/MACD)
        signal = prediction_engine.generate_signal(prices, btc_price=prices[-1])

        assert isinstance(signal, PredictionSignal)
        assert signal.signal in [SignalType.UP, SignalType.DOWN, SignalType.SKIP]
        assert 0.0 <= signal.confidence <= 1.0
        assert signal.reasoning is not None
        assert signal.timestamp is not None
