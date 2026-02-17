"""
Prediction Engine for Polymarket Bot.

This module implements the deterministic rule-based signal generator that
produces trading signals based on technical indicators (RSI, MACD) and
order book imbalance analysis.

The prediction engine:
- Analyzes RSI and MACD indicators for momentum signals
- Incorporates order book imbalance for market pressure assessment
- Generates UP/DOWN/SKIP signals with confidence scores
- Handles edge cases (insufficient data, zero volume, etc.)
- Provides deterministic, rule-based predictions (no ML models)
"""

import logging
from typing import Tuple, Optional
from decimal import Decimal

from .models import MarketData
from .utils import ValidationError, validate_non_empty

# Setup logging
logger = logging.getLogger(__name__)

# Signal type constants
SIGNAL_UP = "UP"
SIGNAL_DOWN = "DOWN"
SIGNAL_SKIP = "SKIP"

# Confidence score constants
CONFIDENCE_HIGH = 75.0
CONFIDENCE_MEDIUM = 60.0
CONFIDENCE_LOW = 45.0
CONFIDENCE_NONE = 0.0

# RSI thresholds
RSI_OVERSOLD = 30.0
RSI_OVERBOUGHT = 70.0
RSI_MODERATE_OVERSOLD = 40.0
RSI_MODERATE_OVERBOUGHT = 60.0

# Order book imbalance thresholds
ORDERBOOK_BULLISH = 1.1  # Bid/Ask ratio > 1.1 indicates buying pressure
ORDERBOOK_BEARISH = 0.9  # Bid/Ask ratio < 0.9 indicates selling pressure


class PredictionError(Exception):
    """Exception raised for prediction-related errors."""
    pass


class InsufficientDataError(PredictionError):
    """Exception raised when there's insufficient data for prediction."""
    pass


def validate_market_data(market_data: MarketData) -> None:
    """
    Validate that market data contains all required fields for prediction.

    Args:
        market_data: MarketData object to validate

    Raises:
        ValidationError: If required data is missing or invalid
    """
    # Check if market_data has the required technical indicator fields
    # Note: The MarketData model needs RSI, MACD, and order book fields
    # For now, we'll add basic validation and extend as needed

    if not hasattr(market_data, 'market_id') or not market_data.market_id:
        raise ValidationError("market_id", "Market ID is required")

    if not hasattr(market_data, 'yes_price') or market_data.yes_price is None:
        raise ValidationError("yes_price", "Yes price is required")

    if not hasattr(market_data, 'no_price') or market_data.no_price is None:
        raise ValidationError("no_price", "No price is required")


def calculate_signal_from_rsi(rsi: float) -> Tuple[Optional[str], str]:
    """
    Generate signal component based on RSI indicator.

    Args:
        rsi: RSI value (0-100)

    Returns:
        Tuple of (signal, reasoning) where signal is UP/DOWN/None and reasoning explains the decision
    """
    if rsi < RSI_OVERSOLD:
        return SIGNAL_UP, f"Strong oversold (RSI={rsi:.1f} < {RSI_OVERSOLD})"
    elif rsi < RSI_MODERATE_OVERSOLD:
        return SIGNAL_UP, f"Moderate oversold (RSI={rsi:.1f} < {RSI_MODERATE_OVERSOLD})"
    elif rsi > RSI_OVERBOUGHT:
        return SIGNAL_DOWN, f"Strong overbought (RSI={rsi:.1f} > {RSI_OVERBOUGHT})"
    elif rsi > RSI_MODERATE_OVERBOUGHT:
        return SIGNAL_DOWN, f"Moderate overbought (RSI={rsi:.1f} > {RSI_MODERATE_OVERBOUGHT})"
    else:
        return None, f"Neutral (RSI={rsi:.1f})"


def calculate_signal_from_macd(macd_line: float, macd_signal: float) -> Tuple[Optional[str], str]:
    """
    Generate signal component based on MACD indicator.

    Args:
        macd_line: MACD line value
        macd_signal: MACD signal line value

    Returns:
        Tuple of (signal, reasoning) where signal is UP/DOWN/None and reasoning explains the decision
    """
    macd_diff = macd_line - macd_signal

    if macd_line > macd_signal:
        if macd_diff > 0.01:  # Strong bullish crossover
            return SIGNAL_UP, f"Strong bullish MACD (line={macd_line:.4f} > signal={macd_signal:.4f}, diff={macd_diff:.4f})"
        else:
            return SIGNAL_UP, f"Bullish MACD (line={macd_line:.4f} > signal={macd_signal:.4f})"
    elif macd_line < macd_signal:
        if macd_diff < -0.01:  # Strong bearish crossover
            return SIGNAL_DOWN, f"Strong bearish MACD (line={macd_line:.4f} < signal={macd_signal:.4f}, diff={macd_diff:.4f})"
        else:
            return SIGNAL_DOWN, f"Bearish MACD (line={macd_line:.4f} < signal={macd_signal:.4f})"
    else:
        return None, f"Neutral MACD (line={macd_line:.4f} ≈ signal={macd_signal:.4f})"


def calculate_signal_from_orderbook(order_book_imbalance: float) -> Tuple[Optional[str], str]:
    """
    Generate signal component based on order book imbalance.

    Args:
        order_book_imbalance: Bid/Ask ratio

    Returns:
        Tuple of (signal, reasoning) where signal is UP/DOWN/None and reasoning explains the decision
    """
    if order_book_imbalance > ORDERBOOK_BULLISH:
        strength = "strong" if order_book_imbalance > 1.2 else "moderate"
        return SIGNAL_UP, f"{strength.capitalize()} buying pressure (bid/ask={order_book_imbalance:.2f} > {ORDERBOOK_BULLISH})"
    elif order_book_imbalance < ORDERBOOK_BEARISH:
        strength = "strong" if order_book_imbalance < 0.8 else "moderate"
        return SIGNAL_DOWN, f"{strength.capitalize()} selling pressure (bid/ask={order_book_imbalance:.2f} < {ORDERBOOK_BEARISH})"
    else:
        return None, f"Balanced order book (bid/ask={order_book_imbalance:.2f})"


def calculate_confidence(
    rsi_signal: Optional[str],
    macd_signal: Optional[str],
    orderbook_signal: Optional[str],
    final_signal: str
) -> float:
    """
    Calculate confidence score based on signal agreement.

    Confidence is higher when multiple indicators agree:
    - All 3 agree: High confidence (75)
    - 2 agree: Medium confidence (60)
    - Only 1 indicator: Low confidence (45)
    - No clear signal: No confidence (0)

    Args:
        rsi_signal: Signal from RSI (UP/DOWN/None)
        macd_signal: Signal from MACD (UP/DOWN/None)
        orderbook_signal: Signal from order book (UP/DOWN/None)
        final_signal: Final decided signal (UP/DOWN/SKIP)

    Returns:
        Confidence score (0-100)
    """
    if final_signal == SIGNAL_SKIP:
        return CONFIDENCE_NONE

    # Count how many indicators agree with the final signal
    agreement_count = 0
    if rsi_signal == final_signal:
        agreement_count += 1
    if macd_signal == final_signal:
        agreement_count += 1
    if orderbook_signal == final_signal:
        agreement_count += 1

    # Return confidence based on agreement
    if agreement_count >= 3:
        return CONFIDENCE_HIGH
    elif agreement_count == 2:
        return CONFIDENCE_MEDIUM
    elif agreement_count == 1:
        return CONFIDENCE_LOW
    else:
        return CONFIDENCE_NONE


def generate_signal(
    rsi: Optional[float] = None,
    macd_line: Optional[float] = None,
    macd_signal: Optional[float] = None,
    order_book_imbalance: Optional[float] = None,
    btc_price: Optional[float] = None
) -> Tuple[str, float]:
    """
    Generate trading signal based on technical indicators.

    This is the main prediction function that combines RSI, MACD, and order book
    imbalance to produce a final trading signal with confidence score.

    Logic:
    1. Analyze each indicator independently
    2. Apply voting mechanism to determine final signal
    3. Calculate confidence based on indicator agreement
    4. Return SKIP if indicators are conflicting or data is insufficient

    Args:
        rsi: RSI(14) value (0-100), None if unavailable
        macd_line: MACD line value, None if unavailable
        macd_signal: MACD signal line value, None if unavailable
        order_book_imbalance: Bid/Ask ratio, None if unavailable
        btc_price: Current BTC price (used for validation), None if unavailable

    Returns:
        Tuple of (signal, confidence_score) where:
        - signal is "UP", "DOWN", or "SKIP"
        - confidence_score is 0-100

    Raises:
        InsufficientDataError: If no indicators are available
        ValidationError: If indicator values are invalid
    """
    # Validate inputs
    available_indicators = 0

    # Validate RSI
    if rsi is not None:
        if not (0 <= rsi <= 100):
            raise ValidationError("rsi", f"RSI must be between 0 and 100, got {rsi}")
        available_indicators += 1

    # Validate MACD (both line and signal must be present or both absent)
    if macd_line is not None and macd_signal is not None:
        available_indicators += 1
    elif macd_line is not None or macd_signal is not None:
        raise ValidationError("macd", "Both MACD line and signal must be provided together")

    # Validate order book imbalance
    if order_book_imbalance is not None:
        if order_book_imbalance < 0:
            raise ValidationError("order_book_imbalance", f"Order book imbalance must be >= 0, got {order_book_imbalance}")
        available_indicators += 1

    # Validate BTC price if provided (sanity check)
    if btc_price is not None:
        if not (1000 <= btc_price <= 1000000):
            logger.warning(f"Unusual BTC price: ${btc_price:.2f} - proceeding with caution")

    # Check if we have enough data
    if available_indicators == 0:
        raise InsufficientDataError("No technical indicators available for prediction")

    logger.info(f"Generating signal with {available_indicators} indicators: "
                f"RSI={rsi}, MACD_line={macd_line}, MACD_signal={macd_signal}, "
                f"OrderBook={order_book_imbalance}, BTC=${btc_price}")

    # Calculate individual signals
    rsi_signal = None
    macd_signal_result = None
    orderbook_signal = None

    reasoning = []

    if rsi is not None:
        rsi_signal, rsi_reason = calculate_signal_from_rsi(rsi)
        reasoning.append(f"RSI: {rsi_reason}")

    if macd_line is not None and macd_signal is not None:
        macd_signal_result, macd_reason = calculate_signal_from_macd(macd_line, macd_signal)
        reasoning.append(f"MACD: {macd_reason}")

    if order_book_imbalance is not None:
        orderbook_signal, orderbook_reason = calculate_signal_from_orderbook(order_book_imbalance)
        reasoning.append(f"Order Book: {orderbook_reason}")

    # Voting mechanism: determine final signal
    signals = [s for s in [rsi_signal, macd_signal_result, orderbook_signal] if s is not None]

    if not signals:
        # No clear signals from any indicator
        logger.info("No clear signals from indicators - returning SKIP. " + "; ".join(reasoning))
        return SIGNAL_SKIP, CONFIDENCE_NONE

    # Count votes for each signal
    up_votes = signals.count(SIGNAL_UP)
    down_votes = signals.count(SIGNAL_DOWN)

    # Determine final signal based on majority vote
    if up_votes > down_votes:
        final_signal = SIGNAL_UP
    elif down_votes > up_votes:
        final_signal = SIGNAL_DOWN
    else:
        # Tie - no clear consensus
        logger.info("Conflicting signals - returning SKIP. " + "; ".join(reasoning))
        return SIGNAL_SKIP, CONFIDENCE_NONE

    # Calculate confidence score
    confidence = calculate_confidence(rsi_signal, macd_signal_result, orderbook_signal, final_signal)

    logger.info(f"Signal generated: {final_signal} with confidence {confidence:.1f}%. " + "; ".join(reasoning))

    return final_signal, confidence


def generate_signal_from_market_data(market_data: MarketData) -> Tuple[str, float]:
    """
    Generate trading signal from MarketData object.

    This is a convenience wrapper around generate_signal() that extracts
    the required technical indicators from a MarketData object.

    Note: This function assumes the MarketData object has been extended
    with technical indicator fields. If not present, it will return SKIP.

    Args:
        market_data: MarketData object containing market and indicator data

    Returns:
        Tuple of (signal, confidence_score)

    Raises:
        ValidationError: If market_data is invalid
    """
    validate_market_data(market_data)

    # Extract technical indicators from market_data if available
    # These fields need to be added to the MarketData model
    rsi = getattr(market_data, 'rsi_14', None)
    macd_line = getattr(market_data, 'macd_line', None)
    macd_signal = getattr(market_data, 'macd_signal', None)
    order_book_imbalance = getattr(market_data, 'order_book_imbalance', None)
    btc_price = getattr(market_data, 'btc_price', None)

    return generate_signal(
        rsi=rsi,
        macd_line=macd_line,
        macd_signal=macd_signal,
        order_book_imbalance=order_book_imbalance,
        btc_price=btc_price
    )
