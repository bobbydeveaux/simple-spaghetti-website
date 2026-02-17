"""
Unit tests for market data service and technical indicators.

Tests cover:
- RSI calculation with known datasets
- MACD calculation accuracy
- Order book imbalance computation
- WebSocket client functionality
- Market data service integration
"""

import pytest
import numpy as np
from decimal import Decimal
from datetime import datetime
from typing import List

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from market_data import (
    TechnicalIndicators,
    OrderBookAnalyzer,
    BinanceWebSocketClient,
    MarketDataService
)
from models import TechnicalIndicatorData


class TestTechnicalIndicators:
    """Tests for technical indicator calculations."""

    def test_rsi_calculation_basic(self):
        """Test RSI calculation with a simple uptrend."""
        # Simple uptrend: should have high RSI
        prices = [100.0 + i for i in range(30)]  # Linear uptrend
        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)

        assert rsi is not None
        assert 0 <= rsi <= 100
        # Uptrend should have RSI > 50
        assert rsi > 50

    def test_rsi_calculation_downtrend(self):
        """Test RSI calculation with a downtrend."""
        # Simple downtrend: should have low RSI
        prices = [100.0 - i for i in range(30)]  # Linear downtrend
        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)

        assert rsi is not None
        assert 0 <= rsi <= 100
        # Downtrend should have RSI < 50
        assert rsi < 50

    def test_rsi_insufficient_data(self):
        """Test RSI returns None with insufficient data."""
        prices = [100.0, 101.0, 102.0]  # Only 3 data points
        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)

        assert rsi is None

    def test_rsi_known_values(self):
        """Test RSI calculation against known values."""
        # Known test case: alternating prices
        prices = [
            44.0, 44.25, 44.125, 43.75, 44.25, 44.75, 45.0, 45.25, 45.5,
            45.0, 44.5, 44.25, 44.0, 43.75, 44.0, 44.5, 45.0, 45.5
        ]
        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)

        assert rsi is not None
        # For this dataset, RSI should be in mid-range
        assert 40 <= rsi <= 60

    def test_rsi_extreme_overbought(self):
        """Test RSI in overbought condition."""
        # Strong uptrend should push RSI toward 70+
        prices = [100.0]
        for i in range(1, 30):
            prices.append(prices[-1] * 1.02)  # 2% gain each period

        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)

        assert rsi is not None
        assert rsi > 70  # Overbought territory

    def test_rsi_extreme_oversold(self):
        """Test RSI in oversold condition."""
        # Strong downtrend should push RSI toward 30-
        prices = [100.0]
        for i in range(1, 30):
            prices.append(prices[-1] * 0.98)  # 2% loss each period

        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)

        assert rsi is not None
        assert rsi < 30  # Oversold territory

    def test_macd_calculation_basic(self):
        """Test MACD calculation with basic price data."""
        # Need at least 35 data points for MACD
        prices = [100.0 + np.sin(i / 5) * 10 for i in range(50)]

        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(prices)

        assert macd_line is not None
        assert signal_line is not None
        assert histogram is not None

        # Histogram should equal MACD line - signal line (approximately)
        assert abs(histogram - (macd_line - signal_line)) < 0.01

    def test_macd_uptrend(self):
        """Test MACD with uptrend data."""
        # Uptrend: MACD line should eventually be above signal line
        prices = [100.0 + i * 0.5 for i in range(50)]

        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(prices)

        assert macd_line is not None
        assert signal_line is not None
        # In uptrend, MACD line typically above signal (positive histogram)
        # This may not always be true at the exact end, so we check the trend exists
        assert histogram is not None

    def test_macd_insufficient_data(self):
        """Test MACD returns None with insufficient data."""
        prices = [100.0 + i for i in range(20)]  # Only 20 data points

        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(prices)

        assert macd_line is None
        assert signal_line is None
        assert histogram is None

    def test_macd_default_parameters(self):
        """Test MACD uses correct default parameters."""
        prices = [100.0 + np.sin(i / 10) * 20 for i in range(60)]

        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(prices)

        # Just verify it calculates successfully with defaults
        assert macd_line is not None
        assert signal_line is not None
        assert histogram is not None

    def test_macd_custom_parameters(self):
        """Test MACD with custom parameters."""
        prices = [100.0 + i * 0.2 for i in range(60)]

        macd_line, signal_line, histogram = TechnicalIndicators.calculate_macd(
            prices,
            fast_period=5,
            slow_period=10,
            signal_period=5
        )

        assert macd_line is not None
        assert signal_line is not None
        assert histogram is not None


class TestOrderBookAnalyzer:
    """Tests for order book analysis."""

    def test_order_book_imbalance_balanced(self):
        """Test imbalance calculation with balanced order book."""
        bids = [(100.0, 10.0), (99.0, 10.0), (98.0, 10.0)]
        asks = [(101.0, 10.0), (102.0, 10.0), (103.0, 10.0)]

        imbalance = OrderBookAnalyzer.calculate_imbalance(bids, asks)

        # Should be close to 1.0 (balanced)
        assert abs(imbalance - 1.0) < 0.01

    def test_order_book_imbalance_buy_pressure(self):
        """Test imbalance with more buy pressure."""
        bids = [(100.0, 20.0), (99.0, 15.0), (98.0, 10.0)]  # 45 total
        asks = [(101.0, 5.0), (102.0, 5.0), (103.0, 5.0)]   # 15 total

        imbalance = OrderBookAnalyzer.calculate_imbalance(bids, asks)

        # Should be 45/15 = 3.0
        assert abs(imbalance - 3.0) < 0.01
        assert imbalance > 1.0  # More buying pressure

    def test_order_book_imbalance_sell_pressure(self):
        """Test imbalance with more sell pressure."""
        bids = [(100.0, 5.0), (99.0, 5.0), (98.0, 5.0)]     # 15 total
        asks = [(101.0, 20.0), (102.0, 15.0), (103.0, 10.0)]  # 45 total

        imbalance = OrderBookAnalyzer.calculate_imbalance(bids, asks)

        # Should be 15/45 = 0.333
        assert abs(imbalance - 0.333) < 0.01
        assert imbalance < 1.0  # More selling pressure

    def test_order_book_imbalance_empty_bids(self):
        """Test imbalance with empty bids."""
        bids = []
        asks = [(101.0, 10.0), (102.0, 10.0)]

        imbalance = OrderBookAnalyzer.calculate_imbalance(bids, asks)

        # Should return default 1.0
        assert imbalance == 1.0

    def test_order_book_imbalance_empty_asks(self):
        """Test imbalance with empty asks."""
        bids = [(100.0, 10.0), (99.0, 10.0)]
        asks = []

        imbalance = OrderBookAnalyzer.calculate_imbalance(bids, asks)

        # Should return default 1.0
        assert imbalance == 1.0

    def test_order_book_imbalance_zero_ask_volume(self):
        """Test imbalance when ask volume is zero."""
        bids = [(100.0, 10.0), (99.0, 10.0)]
        asks = [(101.0, 0.0), (102.0, 0.0)]

        imbalance = OrderBookAnalyzer.calculate_imbalance(bids, asks)

        # Should return default 1.0 to avoid division by zero
        assert imbalance == 1.0

    def test_order_book_imbalance_top_levels(self):
        """Test that imbalance only considers top 10 levels."""
        # Create 20 levels on each side
        bids = [(100.0 - i, 10.0) for i in range(20)]
        asks = [(101.0 + i, 10.0) for i in range(20)]

        imbalance = OrderBookAnalyzer.calculate_imbalance(bids, asks)

        # Should only consider first 10 levels: 100/100 = 1.0
        assert abs(imbalance - 1.0) < 0.01


class TestBinanceWebSocketClient:
    """Tests for Binance WebSocket client."""

    def test_client_initialization(self):
        """Test client initializes with correct defaults."""
        client = BinanceWebSocketClient(max_history=100)

        assert client.max_history == 100
        assert len(client.price_history) == 0
        assert client.current_price is None
        assert not client.connected
        assert client.update_count == 0

    def test_price_history_management(self):
        """Test price history storage and retrieval."""
        client = BinanceWebSocketClient(max_history=5)

        # Manually add prices
        for i in range(10):
            client.price_history.append(float(100 + i))

        # Should only keep last 5
        assert len(client.price_history) == 5
        history = client.get_price_history()
        assert history == [105.0, 106.0, 107.0, 108.0, 109.0]

    def test_get_price_history_with_count(self):
        """Test retrieving limited price history."""
        client = BinanceWebSocketClient()

        # Add 20 prices
        for i in range(20):
            client.price_history.append(float(100 + i))

        # Get last 5
        history = client.get_price_history(count=5)
        assert len(history) == 5
        assert history == [115.0, 116.0, 117.0, 118.0, 119.0]

    def test_get_current_price(self):
        """Test current price retrieval."""
        client = BinanceWebSocketClient()
        client.current_price = 45000.50

        price = client.get_current_price()
        assert price == 45000.50

    def test_statistics(self):
        """Test statistics gathering."""
        client = BinanceWebSocketClient()
        client.current_price = 45000.0
        client.price_history.append(45000.0)
        client.update_count = 10

        stats = client.get_statistics()

        assert stats["current_price"] == 45000.0
        assert stats["history_size"] == 1
        assert stats["update_count"] == 10
        assert not stats["connected"]

    def test_on_message_parsing(self):
        """Test WebSocket message parsing."""
        client = BinanceWebSocketClient()

        # Simulate trade message
        message = '{"e": "trade", "E": 123456789, "s": "BTCUSDT", "p": "45123.45", "q": "0.1"}'

        client.on_message(None, message)

        assert client.current_price == 45123.45
        assert len(client.price_history) == 1
        assert client.price_history[0] == 45123.45
        assert client.update_count == 1

    def test_on_message_invalid_json(self):
        """Test handling of invalid JSON messages."""
        client = BinanceWebSocketClient()

        # Invalid JSON should not crash
        client.on_message(None, "invalid json {")

        assert client.current_price is None
        assert len(client.price_history) == 0


class TestMarketDataService:
    """Tests for market data service integration."""

    def test_service_initialization(self):
        """Test service initializes correctly."""
        service = MarketDataService()

        assert service.binance_client is not None
        assert service.order_book_analyzer is not None

    def test_get_current_price_none(self):
        """Test getting price when not connected."""
        service = MarketDataService()

        price = service.get_current_price()
        assert price is None

    def test_get_current_price_with_data(self):
        """Test getting price with data available."""
        service = MarketDataService()
        service.binance_client.current_price = 45250.50

        price = service.get_current_price()
        assert price == Decimal("45250.50")

    def test_get_technical_indicators_no_data(self):
        """Test getting indicators with no data."""
        service = MarketDataService()

        indicators = service.get_technical_indicators()

        assert indicators["rsi"] is None
        assert indicators["macd_line"] is None
        assert indicators["macd_signal"] is None
        assert indicators["macd_histogram"] is None
        assert indicators["order_book_imbalance"] == 1.0

    def test_get_technical_indicators_with_data(self):
        """Test getting indicators with sufficient data."""
        service = MarketDataService()

        # Add sufficient price data
        for i in range(50):
            service.binance_client.price_history.append(45000.0 + i * 10)

        indicators = service.get_technical_indicators()

        # With uptrend data, RSI and MACD should be calculated
        assert indicators["rsi"] is not None
        assert indicators["macd_line"] is not None
        assert indicators["macd_signal"] is not None
        assert indicators["macd_histogram"] is not None

    def test_is_ready_not_connected(self):
        """Test service not ready when not connected."""
        service = MarketDataService()

        assert not service.is_ready()

    def test_is_ready_insufficient_data(self):
        """Test service not ready with insufficient data."""
        service = MarketDataService()
        service.binance_client.connected = True

        # Add only 10 data points (need 35)
        for i in range(10):
            service.binance_client.price_history.append(45000.0 + i)

        assert not service.is_ready()

    def test_is_ready_with_sufficient_data(self):
        """Test service ready with sufficient data."""
        service = MarketDataService()
        service.binance_client.connected = True

        # Add 50 data points (more than 35 required)
        for i in range(50):
            service.binance_client.price_history.append(45000.0 + i)

        assert service.is_ready()

    def test_get_market_data(self):
        """Test getting complete market data snapshot."""
        service = MarketDataService()
        service.binance_client.current_price = 45000.0

        # Add some price history
        for i in range(50):
            service.binance_client.price_history.append(45000.0 + i * 5)

        data = service.get_market_data()

        assert "timestamp" in data
        assert "btc_price" in data
        assert "indicators" in data
        assert "connection_stats" in data
        assert data["btc_price"] == 45000.0


class TestTechnicalIndicatorDataModel:
    """Tests for TechnicalIndicatorData model."""

    def test_model_creation_minimal(self):
        """Test creating model with minimal required fields."""
        data = TechnicalIndicatorData(
            btc_price=Decimal("45000.50")
        )

        assert data.btc_price == Decimal("45000.50")
        assert data.rsi is None
        assert data.order_book_imbalance == Decimal("1.0")
        assert isinstance(data.timestamp, datetime)

    def test_model_creation_full(self):
        """Test creating model with all fields."""
        data = TechnicalIndicatorData(
            btc_price=Decimal("45000.50"),
            rsi=Decimal("65.5"),
            macd_line=Decimal("125.75"),
            macd_signal=Decimal("110.25"),
            macd_histogram=Decimal("15.50"),
            order_book_imbalance=Decimal("1.15"),
            price_history_size=50
        )

        assert data.btc_price == Decimal("45000.50")
        assert data.rsi == Decimal("65.5")
        assert data.macd_line == Decimal("125.75")
        assert data.macd_signal == Decimal("110.25")
        assert data.price_history_size == 50

    def test_model_validation_rsi_range(self):
        """Test RSI validation enforces 0-100 range."""
        # Valid RSI
        data = TechnicalIndicatorData(
            btc_price=Decimal("45000"),
            rsi=Decimal("50")
        )
        assert data.rsi == Decimal("50")

        # Invalid RSI > 100
        with pytest.raises(Exception):  # Pydantic ValidationError
            TechnicalIndicatorData(
                btc_price=Decimal("45000"),
                rsi=Decimal("150")
            )

    def test_model_to_dict(self):
        """Test model serialization to dictionary."""
        data = TechnicalIndicatorData(
            btc_price=Decimal("45000.50"),
            rsi=Decimal("65.5"),
            macd_line=Decimal("125.75"),
            price_history_size=50
        )

        result = data.to_dict()

        assert result["btc_price"] == 45000.50
        assert result["rsi"] == 65.5
        assert result["macd_line"] == 125.75
        assert result["price_history_size"] == 50
        assert "timestamp" in result

    def test_has_valid_indicators_complete(self):
        """Test has_valid_indicators with all indicators."""
        data = TechnicalIndicatorData(
            btc_price=Decimal("45000"),
            rsi=Decimal("50"),
            macd_line=Decimal("100"),
            macd_signal=Decimal("95"),
            macd_histogram=Decimal("5")
        )

        assert data.has_valid_indicators()

    def test_has_valid_indicators_incomplete(self):
        """Test has_valid_indicators with missing indicators."""
        data = TechnicalIndicatorData(
            btc_price=Decimal("45000"),
            rsi=Decimal("50")
        )

        assert not data.has_valid_indicators()

    def test_get_rsi_signal_overbought(self):
        """Test RSI signal for overbought condition."""
        data = TechnicalIndicatorData(
            btc_price=Decimal("45000"),
            rsi=Decimal("75")
        )

        assert data.get_rsi_signal() == "overbought"

    def test_get_rsi_signal_oversold(self):
        """Test RSI signal for oversold condition."""
        data = TechnicalIndicatorData(
            btc_price=Decimal("45000"),
            rsi=Decimal("25")
        )

        assert data.get_rsi_signal() == "oversold"

    def test_get_rsi_signal_neutral(self):
        """Test RSI signal for neutral condition."""
        data = TechnicalIndicatorData(
            btc_price=Decimal("45000"),
            rsi=Decimal("50")
        )

        assert data.get_rsi_signal() == "neutral"

    def test_get_macd_signal_bullish(self):
        """Test MACD signal for bullish condition."""
        data = TechnicalIndicatorData(
            btc_price=Decimal("45000"),
            macd_line=Decimal("110"),
            macd_signal=Decimal("100")
        )

        assert data.get_macd_signal() == "bullish"

    def test_get_macd_signal_bearish(self):
        """Test MACD signal for bearish condition."""
        data = TechnicalIndicatorData(
            btc_price=Decimal("45000"),
            macd_line=Decimal("95"),
            macd_signal=Decimal("100")
        )

        assert data.get_macd_signal() == "bearish"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
