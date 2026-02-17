"""
Comprehensive test suite for the Prediction Engine.

Tests cover:
- RSI-based signal generation
- MACD-based signal generation
- Order book imbalance analysis
- Signal combination and voting mechanism
- Confidence score calculation
- Edge case handling (insufficient data, invalid inputs, etc.)
- Integration with MarketData model
"""

import pytest
import sys
from pathlib import Path
from decimal import Decimal
from datetime import datetime

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from prediction import (
    generate_signal,
    generate_signal_from_market_data,
    calculate_signal_from_rsi,
    calculate_signal_from_macd,
    calculate_signal_from_orderbook,
    calculate_confidence,
    validate_market_data,
    InsufficientDataError,
    PredictionError,
    SIGNAL_UP,
    SIGNAL_DOWN,
    SIGNAL_SKIP,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_LOW,
    CONFIDENCE_NONE,
    RSI_OVERSOLD,
    RSI_OVERBOUGHT,
    ORDERBOOK_BULLISH,
    ORDERBOOK_BEARISH
)
from models import MarketData
from utils import ValidationError


class TestCalculateSignalFromRSI:
    """Test RSI signal calculation."""

    def test_strong_oversold_signal(self):
        """Test RSI < 30 generates UP signal."""
        signal, reason = calculate_signal_from_rsi(25.0)
        assert signal == SIGNAL_UP
        assert "oversold" in reason.lower()
        assert "25.0" in reason

    def test_moderate_oversold_signal(self):
        """Test RSI between 30-40 generates UP signal."""
        signal, reason = calculate_signal_from_rsi(35.0)
        assert signal == SIGNAL_UP
        assert "oversold" in reason.lower()

    def test_strong_overbought_signal(self):
        """Test RSI > 70 generates DOWN signal."""
        signal, reason = calculate_signal_from_rsi(75.0)
        assert signal == SIGNAL_DOWN
        assert "overbought" in reason.lower()
        assert "75.0" in reason

    def test_moderate_overbought_signal(self):
        """Test RSI between 60-70 generates DOWN signal."""
        signal, reason = calculate_signal_from_rsi(65.0)
        assert signal == SIGNAL_DOWN
        assert "overbought" in reason.lower()

    def test_neutral_rsi_signal(self):
        """Test RSI between 40-60 generates no signal."""
        signal, reason = calculate_signal_from_rsi(50.0)
        assert signal is None
        assert "neutral" in reason.lower()

    def test_boundary_values(self):
        """Test RSI boundary values."""
        # Just below oversold threshold
        signal, _ = calculate_signal_from_rsi(29.9)
        assert signal == SIGNAL_UP

        # Just at oversold threshold
        signal, _ = calculate_signal_from_rsi(30.0)
        assert signal == SIGNAL_UP

        # Just above overbought threshold
        signal, _ = calculate_signal_from_rsi(70.1)
        assert signal == SIGNAL_DOWN

        # Just at overbought threshold
        signal, _ = calculate_signal_from_rsi(70.0)
        assert signal == SIGNAL_DOWN


class TestCalculateSignalFromMACD:
    """Test MACD signal calculation."""

    def test_strong_bullish_macd(self):
        """Test MACD line significantly above signal line."""
        signal, reason = calculate_signal_from_macd(0.05, 0.02)
        assert signal == SIGNAL_UP
        assert "bullish" in reason.lower()

    def test_weak_bullish_macd(self):
        """Test MACD line slightly above signal line."""
        signal, reason = calculate_signal_from_macd(0.015, 0.010)
        assert signal == SIGNAL_UP
        assert "bullish" in reason.lower()

    def test_strong_bearish_macd(self):
        """Test MACD line significantly below signal line."""
        signal, reason = calculate_signal_from_macd(-0.05, -0.02)
        assert signal == SIGNAL_DOWN
        assert "bearish" in reason.lower()

    def test_weak_bearish_macd(self):
        """Test MACD line slightly below signal line."""
        signal, reason = calculate_signal_from_macd(0.010, 0.015)
        assert signal == SIGNAL_DOWN
        assert "bearish" in reason.lower()

    def test_neutral_macd(self):
        """Test MACD line equal to signal line."""
        signal, reason = calculate_signal_from_macd(0.0, 0.0)
        assert signal is None
        assert "neutral" in reason.lower()

    def test_macd_with_negative_values(self):
        """Test MACD works correctly with negative values."""
        # Bullish: line > signal even when both negative
        signal, _ = calculate_signal_from_macd(-0.01, -0.05)
        assert signal == SIGNAL_UP

        # Bearish: line < signal when both negative
        signal, _ = calculate_signal_from_macd(-0.05, -0.01)
        assert signal == SIGNAL_DOWN


class TestCalculateSignalFromOrderbook:
    """Test order book imbalance signal calculation."""

    def test_strong_buying_pressure(self):
        """Test high bid/ask ratio generates UP signal."""
        signal, reason = calculate_signal_from_orderbook(1.5)
        assert signal == SIGNAL_UP
        assert "buying pressure" in reason.lower()
        assert "1.50" in reason

    def test_moderate_buying_pressure(self):
        """Test moderate bid/ask ratio generates UP signal."""
        signal, reason = calculate_signal_from_orderbook(1.15)
        assert signal == SIGNAL_UP
        assert "buying pressure" in reason.lower()

    def test_strong_selling_pressure(self):
        """Test low bid/ask ratio generates DOWN signal."""
        signal, reason = calculate_signal_from_orderbook(0.7)
        assert signal == SIGNAL_DOWN
        assert "selling pressure" in reason.lower()

    def test_moderate_selling_pressure(self):
        """Test moderate low bid/ask ratio generates DOWN signal."""
        signal, reason = calculate_signal_from_orderbook(0.85)
        assert signal == SIGNAL_DOWN
        assert "selling pressure" in reason.lower()

    def test_balanced_orderbook(self):
        """Test balanced order book generates no signal."""
        signal, reason = calculate_signal_from_orderbook(1.0)
        assert signal is None
        assert "balanced" in reason.lower()

    def test_boundary_values(self):
        """Test order book boundary values."""
        # Just above bullish threshold
        signal, _ = calculate_signal_from_orderbook(1.11)
        assert signal == SIGNAL_UP

        # Just below bearish threshold
        signal, _ = calculate_signal_from_orderbook(0.89)
        assert signal == SIGNAL_DOWN


class TestCalculateConfidence:
    """Test confidence score calculation."""

    def test_all_three_agree_high_confidence(self):
        """Test all indicators agreeing produces high confidence."""
        confidence = calculate_confidence(SIGNAL_UP, SIGNAL_UP, SIGNAL_UP, SIGNAL_UP)
        assert confidence == CONFIDENCE_HIGH

    def test_two_agree_medium_confidence(self):
        """Test two indicators agreeing produces medium confidence."""
        confidence = calculate_confidence(SIGNAL_UP, SIGNAL_UP, None, SIGNAL_UP)
        assert confidence == CONFIDENCE_MEDIUM

        confidence = calculate_confidence(SIGNAL_UP, None, SIGNAL_UP, SIGNAL_UP)
        assert confidence == CONFIDENCE_MEDIUM

    def test_one_agrees_low_confidence(self):
        """Test single indicator produces low confidence."""
        confidence = calculate_confidence(SIGNAL_UP, None, None, SIGNAL_UP)
        assert confidence == CONFIDENCE_LOW

    def test_skip_signal_zero_confidence(self):
        """Test SKIP signal always has zero confidence."""
        confidence = calculate_confidence(SIGNAL_UP, SIGNAL_DOWN, None, SIGNAL_SKIP)
        assert confidence == CONFIDENCE_NONE

    def test_conflicting_signals_low_confidence(self):
        """Test conflicting signals produce low or no confidence."""
        # UP signal but DOWN and None disagree
        confidence = calculate_confidence(SIGNAL_UP, SIGNAL_DOWN, None, SIGNAL_UP)
        assert confidence == CONFIDENCE_LOW


class TestGenerateSignal:
    """Test main signal generation function."""

    def test_strong_bullish_all_indicators_agree(self):
        """Test strong bullish signal when all indicators agree."""
        signal, confidence = generate_signal(
            rsi=25.0,  # Oversold
            macd_line=0.05,
            macd_signal=0.02,  # Bullish crossover
            order_book_imbalance=1.3,  # Strong buying pressure
            btc_price=50000.0
        )
        assert signal == SIGNAL_UP
        assert confidence == CONFIDENCE_HIGH

    def test_strong_bearish_all_indicators_agree(self):
        """Test strong bearish signal when all indicators agree."""
        signal, confidence = generate_signal(
            rsi=75.0,  # Overbought
            macd_line=-0.05,
            macd_signal=-0.02,  # Bearish crossover
            order_book_imbalance=0.7,  # Strong selling pressure
            btc_price=50000.0
        )
        assert signal == SIGNAL_DOWN
        assert confidence == CONFIDENCE_HIGH

    def test_moderate_bullish_two_indicators(self):
        """Test moderate bullish signal with two agreeing indicators."""
        signal, confidence = generate_signal(
            rsi=35.0,  # Moderate oversold - UP
            macd_line=0.015,
            macd_signal=0.010,  # Bullish - UP
            order_book_imbalance=1.0,  # Neutral - None
            btc_price=50000.0
        )
        assert signal == SIGNAL_UP
        assert confidence == CONFIDENCE_MEDIUM

    def test_conflicting_signals_skip(self):
        """Test conflicting signals produce SKIP."""
        signal, confidence = generate_signal(
            rsi=25.0,  # Oversold - UP
            macd_line=-0.05,
            macd_signal=-0.02,  # Bearish - DOWN
            order_book_imbalance=1.0,  # Neutral - None
            btc_price=50000.0
        )
        # 1 UP, 1 DOWN, 1 None -> tie -> SKIP
        assert signal == SIGNAL_SKIP
        assert confidence == CONFIDENCE_NONE

    def test_single_indicator_rsi_only(self):
        """Test signal generation with only RSI."""
        signal, confidence = generate_signal(
            rsi=25.0,
            btc_price=50000.0
        )
        assert signal == SIGNAL_UP
        assert confidence == CONFIDENCE_LOW

    def test_single_indicator_macd_only(self):
        """Test signal generation with only MACD."""
        signal, confidence = generate_signal(
            macd_line=0.05,
            macd_signal=0.02,
            btc_price=50000.0
        )
        assert signal == SIGNAL_UP
        assert confidence == CONFIDENCE_LOW

    def test_single_indicator_orderbook_only(self):
        """Test signal generation with only order book."""
        signal, confidence = generate_signal(
            order_book_imbalance=0.7,
            btc_price=50000.0
        )
        assert signal == SIGNAL_DOWN
        assert confidence == CONFIDENCE_LOW

    def test_all_neutral_indicators_skip(self):
        """Test all neutral indicators produce SKIP."""
        signal, confidence = generate_signal(
            rsi=50.0,  # Neutral
            macd_line=0.0,
            macd_signal=0.0,  # Neutral
            order_book_imbalance=1.0,  # Neutral
            btc_price=50000.0
        )
        assert signal == SIGNAL_SKIP
        assert confidence == CONFIDENCE_NONE


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_no_indicators_raises_error(self):
        """Test that having no indicators raises InsufficientDataError."""
        with pytest.raises(InsufficientDataError):
            generate_signal()

    def test_invalid_rsi_out_of_range_high(self):
        """Test invalid RSI > 100 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            generate_signal(rsi=150.0)
        assert "rsi" in str(exc_info.value).lower()

    def test_invalid_rsi_out_of_range_low(self):
        """Test invalid RSI < 0 raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            generate_signal(rsi=-10.0)
        assert "rsi" in str(exc_info.value).lower()

    def test_macd_line_without_signal_raises_error(self):
        """Test MACD line without signal raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            generate_signal(macd_line=0.05)
        assert "macd" in str(exc_info.value).lower()

    def test_macd_signal_without_line_raises_error(self):
        """Test MACD signal without line raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            generate_signal(macd_signal=0.02)
        assert "macd" in str(exc_info.value).lower()

    def test_negative_orderbook_imbalance_raises_error(self):
        """Test negative order book imbalance raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            generate_signal(order_book_imbalance=-0.5)
        assert "order_book_imbalance" in str(exc_info.value).lower()

    def test_zero_orderbook_imbalance_valid(self):
        """Test zero order book imbalance is valid (extreme selling pressure)."""
        signal, confidence = generate_signal(order_book_imbalance=0.0)
        assert signal == SIGNAL_DOWN  # Zero bid/ask is extreme selling
        assert confidence == CONFIDENCE_LOW

    def test_unusual_btc_price_logs_warning(self, caplog):
        """Test unusual BTC price logs warning but continues."""
        import logging
        caplog.set_level(logging.WARNING)

        # Very low price
        signal, _ = generate_signal(rsi=50.0, btc_price=500.0)
        assert "Unusual BTC price" in caplog.text

        caplog.clear()

        # Very high price
        signal, _ = generate_signal(rsi=50.0, btc_price=1500000.0)
        assert "Unusual BTC price" in caplog.text

    def test_valid_btc_price_range(self):
        """Test valid BTC prices don't raise errors."""
        # Low end of valid range
        signal, _ = generate_signal(rsi=50.0, btc_price=1000.0)
        assert signal == SIGNAL_SKIP

        # High end of valid range
        signal, _ = generate_signal(rsi=50.0, btc_price=1000000.0)
        assert signal == SIGNAL_SKIP

        # Typical price
        signal, _ = generate_signal(rsi=50.0, btc_price=50000.0)
        assert signal == SIGNAL_SKIP

    def test_boundary_rsi_values(self):
        """Test RSI at exact boundary values."""
        # RSI = 0 (extreme oversold)
        signal, _ = generate_signal(rsi=0.0)
        assert signal == SIGNAL_UP

        # RSI = 100 (extreme overbought)
        signal, _ = generate_signal(rsi=100.0)
        assert signal == SIGNAL_DOWN

        # RSI = 30 (at oversold threshold)
        signal, _ = generate_signal(rsi=30.0)
        assert signal == SIGNAL_UP

        # RSI = 70 (at overbought threshold)
        signal, _ = generate_signal(rsi=70.0)
        assert signal == SIGNAL_DOWN


class TestGenerateSignalFromMarketData:
    """Test signal generation from MarketData objects."""

    def test_market_data_without_indicators_raises_error(self):
        """Test MarketData without technical indicators raises error."""
        market_data = MarketData(
            market_id="test_market_123",
            question="Will BTC reach $100k?",
            end_date=datetime.utcnow(),
            yes_price=Decimal("0.65"),
            no_price=Decimal("0.35")
        )

        # Should raise InsufficientDataError since no indicators are present
        with pytest.raises(InsufficientDataError):
            generate_signal_from_market_data(market_data)

    def test_market_data_validation_missing_id(self):
        """Test validation catches missing market_id."""
        # Create an object with missing market_id
        market_data = type('MockMarketData', (), {
            'market_id': None,
            'yes_price': Decimal("0.5"),
            'no_price': Decimal("0.5")
        })()

        with pytest.raises(ValidationError):
            validate_market_data(market_data)

    def test_market_data_validation_missing_prices(self):
        """Test validation catches missing prices."""
        # Missing yes_price
        market_data = type('MockMarketData', (), {
            'market_id': "test_123",
            'yes_price': None,
            'no_price': Decimal("0.5")
        })()

        with pytest.raises(ValidationError):
            validate_market_data(market_data)


class TestIntegrationScenarios:
    """Test realistic trading scenarios."""

    def test_strong_bullish_breakout_scenario(self):
        """
        Scenario: BTC breaking out from oversold with strong momentum.
        - RSI recovering from oversold (35)
        - MACD showing bullish crossover
        - Strong buying pressure in order book
        """
        signal, confidence = generate_signal(
            rsi=35.0,
            macd_line=0.03,
            macd_signal=0.01,
            order_book_imbalance=1.4,
            btc_price=48000.0
        )
        assert signal == SIGNAL_UP
        assert confidence >= CONFIDENCE_MEDIUM

    def test_strong_bearish_breakdown_scenario(self):
        """
        Scenario: BTC breaking down from overbought with strong momentum.
        - RSI in overbought (75)
        - MACD showing bearish crossover
        - Strong selling pressure in order book
        """
        signal, confidence = generate_signal(
            rsi=75.0,
            macd_line=-0.03,
            macd_signal=-0.01,
            order_book_imbalance=0.6,
            btc_price=52000.0
        )
        assert signal == SIGNAL_DOWN
        assert confidence >= CONFIDENCE_MEDIUM

    def test_consolidation_phase_scenario(self):
        """
        Scenario: BTC in consolidation with no clear direction.
        - RSI neutral (50)
        - MACD flat
        - Balanced order book
        """
        signal, confidence = generate_signal(
            rsi=50.0,
            macd_line=0.001,
            macd_signal=0.001,
            order_book_imbalance=1.0,
            btc_price=50000.0
        )
        assert signal == SIGNAL_SKIP
        assert confidence == CONFIDENCE_NONE

    def test_false_signal_scenario(self):
        """
        Scenario: RSI oversold but other indicators bearish (potential false signal).
        - RSI oversold (28)
        - MACD bearish
        - Selling pressure
        Should produce conflicting signals and SKIP
        """
        signal, confidence = generate_signal(
            rsi=28.0,
            macd_line=-0.02,
            macd_signal=0.01,
            order_book_imbalance=0.7,
            btc_price=45000.0
        )
        # RSI says UP, but MACD and orderbook say DOWN -> conflicting -> SKIP
        assert signal == SIGNAL_SKIP or confidence <= CONFIDENCE_LOW

    def test_partial_data_scenario(self):
        """
        Scenario: Only some indicators available (data feed issues).
        Should still produce signal with lower confidence.
        """
        signal, confidence = generate_signal(
            rsi=30.0,
            macd_line=0.02,
            macd_signal=0.01,
            # No order book data
            btc_price=50000.0
        )
        # Both indicators bullish
        assert signal == SIGNAL_UP
        assert confidence == CONFIDENCE_MEDIUM


class TestSignalConsistency:
    """Test signal generation consistency and determinism."""

    def test_same_inputs_same_output(self):
        """Test that same inputs always produce same output (determinism)."""
        inputs = {
            'rsi': 35.0,
            'macd_line': 0.02,
            'macd_signal': 0.01,
            'order_book_imbalance': 1.2,
            'btc_price': 50000.0
        }

        results = [generate_signal(**inputs) for _ in range(10)]

        # All results should be identical
        assert len(set(results)) == 1

    def test_small_changes_near_thresholds(self):
        """Test behavior near decision thresholds."""
        # Just below RSI oversold threshold
        signal1, _ = generate_signal(rsi=29.9)
        # Just above RSI oversold threshold
        signal2, _ = generate_signal(rsi=30.1)

        # Both should be UP (oversold)
        assert signal1 == SIGNAL_UP
        assert signal2 == SIGNAL_UP

    def test_confidence_monotonicity(self):
        """Test that confidence increases with more agreeing indicators."""
        # 1 indicator
        _, conf1 = generate_signal(rsi=25.0)

        # 2 indicators agreeing
        _, conf2 = generate_signal(rsi=25.0, macd_line=0.02, macd_signal=0.01)

        # 3 indicators agreeing
        _, conf3 = generate_signal(
            rsi=25.0,
            macd_line=0.02,
            macd_signal=0.01,
            order_book_imbalance=1.3
        )

        # Confidence should increase
        assert conf1 < conf2 < conf3
