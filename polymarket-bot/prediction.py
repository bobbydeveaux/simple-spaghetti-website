"""
Prediction Engine for Polymarket Bot.

This module implements the prediction engine that generates trading signals
based on technical indicators (RSI, MACD) and order book imbalance.

The prediction engine follows a deterministic signal generation algorithm:
- UP signal: RSI oversold + MACD bullish + strong buying pressure
- DOWN signal: RSI overbought + MACD bearish + strong selling pressure
- SKIP signal: Conditions don't meet criteria for UP or DOWN

All signals include confidence scores and reasoning for transparency.
"""

import logging
from typing import List, Tuple, Optional
from decimal import Decimal
from datetime import datetime, timezone

from .config import Config, get_config
from .models import PredictionSignal, SignalType
from .market_data import calculate_rsi, calculate_macd, get_order_book_imbalance


# Setup logging
logger = logging.getLogger(__name__)


class PredictionError(Exception):
    """Exception raised for prediction engine errors."""
    pass


class PredictionEngine:
    """
    Prediction engine for generating trading signals.

    Uses technical indicators (RSI, MACD) and order book imbalance
    to generate deterministic UP/DOWN/SKIP signals with confidence scores.
    """

    def __init__(self, config: Optional[Config] = None):
        """
        Initialize the prediction engine.

        Args:
            config: Configuration object. If None, loads from environment.
        """
        self.config = config if config else get_config()
        logger.info(
            f"Initialized PredictionEngine with "
            f"RSI({self.config.rsi_period}, oversold={self.config.rsi_oversold_threshold}, "
            f"overbought={self.config.rsi_overbought_threshold}), "
            f"MACD({self.config.macd_fast_period}, {self.config.macd_slow_period}, "
            f"{self.config.macd_signal_period})"
        )

    def generate_signal(
        self,
        prices: List[float],
        btc_price: Optional[float] = None
    ) -> PredictionSignal:
        """
        Generate a trading signal based on technical indicators.

        Args:
            prices: List of historical prices (oldest to newest)
            btc_price: Current BTC price (optional, for context)

        Returns:
            PredictionSignal with signal type, confidence, and reasoning

        Raises:
            PredictionError: If unable to generate signal due to insufficient data
        """
        try:
            # Calculate technical indicators
            rsi = self._calculate_rsi(prices)
            macd_line, macd_signal = self._calculate_macd(prices)
            order_book_imbalance = self._get_order_book_imbalance()

            logger.debug(
                f"Indicators - RSI: {rsi:.2f}, MACD: {macd_line:.2f}, "
                f"Signal: {macd_signal:.2f}, OB Imbalance: {order_book_imbalance:.2f}"
            )

            # Generate signal based on indicator conditions
            signal, confidence, reasoning = self._evaluate_conditions(
                rsi=rsi,
                macd_line=macd_line,
                macd_signal=macd_signal,
                order_book_imbalance=order_book_imbalance
            )

            # Create prediction signal
            prediction = PredictionSignal(
                signal=signal,
                confidence=Decimal(str(confidence)),
                rsi=Decimal(str(rsi)),
                macd_line=Decimal(str(macd_line)),
                macd_signal=Decimal(str(macd_signal)),
                order_book_imbalance=Decimal(str(order_book_imbalance)),
                btc_price=Decimal(str(btc_price)) if btc_price else None,
                timestamp=datetime.now(timezone.utc),
                reasoning=reasoning
            )

            logger.info(
                f"Generated signal: {signal.value.upper()} "
                f"(confidence: {confidence:.2f}) - {reasoning}"
            )

            return prediction

        except ValueError as e:
            raise PredictionError(f"Failed to generate signal: {str(e)}") from e
        except Exception as e:
            raise PredictionError(f"Unexpected error generating signal: {str(e)}") from e

    def _calculate_rsi(self, prices: List[float]) -> float:
        """
        Calculate RSI using configured period.

        Args:
            prices: List of historical prices

        Returns:
            RSI value (0-100)

        Raises:
            ValueError: If insufficient price data
        """
        return calculate_rsi(prices, period=self.config.rsi_period)

    def _calculate_macd(self, prices: List[float]) -> Tuple[float, float]:
        """
        Calculate MACD with configured periods.

        Args:
            prices: List of historical prices

        Returns:
            Tuple of (macd_line, signal_line)

        Raises:
            ValueError: If insufficient price data
        """
        return calculate_macd(
            prices,
            fast_period=self.config.macd_fast_period,
            slow_period=self.config.macd_slow_period,
            signal_period=self.config.macd_signal_period
        )

    def _get_order_book_imbalance(self) -> float:
        """
        Get current order book imbalance.

        Returns:
            Order book imbalance ratio

        Raises:
            ConnectionError: If unable to fetch order book data
        """
        return get_order_book_imbalance()

    def _evaluate_conditions(
        self,
        rsi: float,
        macd_line: float,
        macd_signal: float,
        order_book_imbalance: float
    ) -> Tuple[SignalType, float, str]:
        """
        Evaluate indicator conditions to generate signal.

        Logic:
        - UP: RSI < oversold_threshold AND MACD > signal AND imbalance > bullish_threshold
        - DOWN: RSI > overbought_threshold AND MACD < signal AND imbalance < bearish_threshold
        - SKIP: Otherwise

        Args:
            rsi: RSI value
            macd_line: MACD line value
            macd_signal: MACD signal line value
            order_book_imbalance: Order book imbalance ratio

        Returns:
            Tuple of (signal_type, confidence, reasoning)
        """
        # Check for UP signal
        if (
            rsi < self.config.rsi_oversold_threshold
            and macd_line > macd_signal
            and order_book_imbalance > self.config.order_book_bullish_threshold
        ):
            reasoning = (
                f"RSI oversold ({rsi:.2f} < {self.config.rsi_oversold_threshold}), "
                f"MACD bullish crossover ({macd_line:.2f} > {macd_signal:.2f}), "
                f"strong buying pressure (imbalance {order_book_imbalance:.2f} > "
                f"{self.config.order_book_bullish_threshold})"
            )
            return SignalType.UP, self.config.prediction_confidence_score, reasoning

        # Check for DOWN signal
        if (
            rsi > self.config.rsi_overbought_threshold
            and macd_line < macd_signal
            and order_book_imbalance < self.config.order_book_bearish_threshold
        ):
            reasoning = (
                f"RSI overbought ({rsi:.2f} > {self.config.rsi_overbought_threshold}), "
                f"MACD bearish crossover ({macd_line:.2f} < {macd_signal:.2f}), "
                f"strong selling pressure (imbalance {order_book_imbalance:.2f} < "
                f"{self.config.order_book_bearish_threshold})"
            )
            return SignalType.DOWN, self.config.prediction_confidence_score, reasoning

        # SKIP signal
        reasoning = (
            f"No clear signal - RSI: {rsi:.2f}, "
            f"MACD: {macd_line:.2f}/{macd_signal:.2f}, "
            f"OB imbalance: {order_book_imbalance:.2f}"
        )
        return SignalType.SKIP, 0.0, reasoning

    def validate_price_data(self, prices: List[float]) -> bool:
        """
        Validate that price data is sufficient for signal generation.

        Args:
            prices: List of historical prices

        Returns:
            True if price data is sufficient, False otherwise
        """
        # Need enough data for MACD (most restrictive)
        min_required = max(
            self.config.rsi_period + 1,
            self.config.macd_slow_period + self.config.macd_signal_period
        )

        if len(prices) < min_required:
            logger.warning(
                f"Insufficient price data: need {min_required}, got {len(prices)}"
            )
            return False

        # Validate prices are positive
        if any(p <= 0 for p in prices):
            logger.warning("Invalid price data: contains non-positive values")
            return False

        return True


def generate_signal_from_market_data(
    prices: List[float],
    btc_price: Optional[float] = None,
    config: Optional[Config] = None
) -> PredictionSignal:
    """
    Convenience function to generate a signal from market data.

    This is a wrapper around PredictionEngine.generate_signal() for
    simple use cases where you don't need to maintain engine state.

    Args:
        prices: List of historical prices (oldest to newest)
        btc_price: Current BTC price (optional, for context)
        config: Configuration object. If None, loads from environment.

    Returns:
        PredictionSignal with signal type, confidence, and reasoning

    Raises:
        PredictionError: If unable to generate signal
    """
    engine = PredictionEngine(config=config)
    return engine.generate_signal(prices=prices, btc_price=btc_price)


def validate_signal_conditions(
    rsi: float,
    macd_line: float,
    macd_signal: float,
    order_book_imbalance: float,
    config: Optional[Config] = None
) -> SignalType:
    """
    Test helper to validate signal conditions directly.

    Args:
        rsi: RSI value
        macd_line: MACD line value
        macd_signal: MACD signal line value
        order_book_imbalance: Order book imbalance ratio
        config: Configuration object. If None, loads from environment.

    Returns:
        SignalType based on conditions
    """
    cfg = config if config else get_config()
    engine = PredictionEngine(config=cfg)
    signal, _, _ = engine._evaluate_conditions(
        rsi=rsi,
        macd_line=macd_line,
        macd_signal=macd_signal,
        order_book_imbalance=order_book_imbalance
    )
    return signal
