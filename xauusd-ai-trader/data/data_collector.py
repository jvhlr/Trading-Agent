"""
XAUUSD AI Trading Research System — Historical Data Collector

Retrieves historical OHLCV + spread data from MetaTrader 5, normalizes
timestamps to UTC, and records field availability. Does NOT fabricate
any data fields that are unavailable from the broker.

Safety: This module performs NO trading operations. It is read-only.
"""

import logging
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd
import numpy as np

from data.mt5_connector import MT5_AVAILABLE, MT5Connector, TIMEFRAME_MAP

if MT5_AVAILABLE:
    import MetaTrader5 as mt5

logger = logging.getLogger(__name__)


@dataclass
class CollectionMetadata:
    """Metadata recorded alongside each data collection."""
    symbol: str
    broker_symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    collection_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "MT5"
    row_count: int = 0
    available_fields: tuple[str, ...] = ()
    unavailable_fields: tuple[str, ...] = ()

    def summary(self) -> str:
        return (
            f"Collection: {self.broker_symbol} ({self.symbol}) {self.timeframe}\n"
            f"  Period: {self.start_date.isoformat()} -> {self.end_date.isoformat()}\n"
            f"  Rows: {self.row_count}\n"
            f"  Source: {self.source}\n"
            f"  Collected: {self.collection_timestamp.isoformat()}\n"
            f"  Available: {', '.join(self.available_fields)}\n"
            f"  Unavailable: {', '.join(self.unavailable_fields) or 'none'}"
        )


# Expected columns from MT5 copy_rates_range:
# time, open, high, low, close, tick_volume, spread, real_volume
MT5_COLUMNS = ["time", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"]

# Our standardized column names
STANDARD_COLUMNS = [
    "timestamp", "open", "high", "low", "close",
    "tick_volume", "spread", "real_volume",
]


def collect_historical(
    connector: MT5Connector,
    broker_symbol: str,
    timeframe: str,
    start: datetime,
    end: datetime,
    internal_symbol: str = "XAUUSD",
) -> tuple[Optional[pd.DataFrame], Optional[CollectionMetadata]]:
    """
    Retrieve historical OHLCV data from MT5.

    Args:
        connector: An active MT5Connector instance.
        broker_symbol: The broker's symbol name (e.g., 'XAUUSDm').
        timeframe: Timeframe string (e.g., 'H1', 'M15').
        start: Start datetime (UTC).
        end: End datetime (UTC).
        internal_symbol: Our internal name (always 'XAUUSD').

    Returns:
        (DataFrame, CollectionMetadata) on success, (None, None) on failure.
        The DataFrame has UTC timestamps and standardized column names.
        Fields that are all-zero or unavailable are noted in metadata
        but NOT fabricated or removed.
    """
    if not connector.is_connected:
        logger.error("Cannot collect data: MT5 not connected.")
        return None, None

    if timeframe not in TIMEFRAME_MAP:
        logger.error("Unknown timeframe '%s'. Known: %s", timeframe, list(TIMEFRAME_MAP.keys()))
        return None, None

    mt5_timeframe = TIMEFRAME_MAP[timeframe]

    # Ensure dates are UTC
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)

    logger.info(
        "Collecting %s %s data: %s -> %s",
        broker_symbol, timeframe,
        start.isoformat(), end.isoformat(),
    )

    # Fetch from MT5
    rates = mt5.copy_rates_range(broker_symbol, mt5_timeframe, start, end)

    if rates is None or len(rates) == 0:
        error = mt5.last_error() if MT5_AVAILABLE else "MT5 not available"
        logger.error("No data returned for %s %s: %s", broker_symbol, timeframe, error)
        return None, None

    # Convert to DataFrame
    df = pd.DataFrame(rates)
    logger.info("Received %d candles from MT5.", len(df))

    # ── Normalize timestamps to UTC ──────────────────────────────────────
    # MT5 returns 'time' as Unix timestamp (seconds since epoch, UTC).
    df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
    df = df.drop(columns=["time"])

    # Reorder columns to our standard
    available = []
    unavailable = []

    for col in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
        if col in df.columns:
            available.append(col)
            # Check if field is actually populated (not all zeros)
            if df[col].eq(0).all() and col not in ("tick_volume", "real_volume"):
                logger.warning(
                    "Field '%s' is all zeros — may be unavailable from broker. "
                    "Recording as available but potentially empty.",
                    col,
                )
        else:
            unavailable.append(col)

    available.insert(0, "timestamp")

    # Sort by timestamp (should already be sorted, but enforce it)
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Build metadata
    metadata = CollectionMetadata(
        symbol=internal_symbol,
        broker_symbol=broker_symbol,
        timeframe=timeframe,
        start_date=start,
        end_date=end,
        row_count=len(df),
        available_fields=tuple(available),
        unavailable_fields=tuple(unavailable),
    )

    logger.info("Collection complete.\n%s", metadata.summary())

    return df, metadata


def generate_sample_data(
    timeframe: str = "H1",
    days: int = 30,
    internal_symbol: str = "XAUUSD",
    base_price: float = 2650.0,
) -> tuple[pd.DataFrame, CollectionMetadata]:
    """
    Generate synthetic XAUUSD sample data for development/testing
    when MT5 is not available.

    This data is CLEARLY LABELED as synthetic and must NEVER be used
    for research conclusions. It exists solely to allow code development
    and testing of the data pipeline.

    Args:
        timeframe: Timeframe to simulate (affects candle count).
        days: Number of days of data to generate.
        internal_symbol: Internal symbol name.
        base_price: Starting price.

    Returns:
        (DataFrame, CollectionMetadata) with synthetic data.
    """
    # Calculate number of candles based on timeframe
    candles_per_day = {
        "M1": 1440, "M5": 288, "M15": 96,
        "H1": 24, "H4": 6, "D1": 1,
    }
    cpd = candles_per_day.get(timeframe, 24)
    n_candles = cpd * days

    # Timeframe interval in minutes
    tf_minutes = {
        "M1": 1, "M5": 5, "M15": 15,
        "H1": 60, "H4": 240, "D1": 1440,
    }
    interval = timedelta(minutes=tf_minutes.get(timeframe, 60))

    end = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    start = end - timedelta(days=days)

    # Generate timestamps (skip weekends for realism)
    timestamps = []
    current = start
    while len(timestamps) < n_candles and current < end:
        if current.weekday() < 5:  # Monday=0 through Friday=4
            timestamps.append(current)
        current += interval

    n_candles = len(timestamps)

    # Generate random walk price data
    rng = np.random.default_rng(seed=42)  # Fixed seed for reproducibility
    returns = rng.normal(0, 0.001, n_candles)  # ~0.1% per candle std
    prices = base_price * np.exp(np.cumsum(returns))

    # Generate OHLC from close prices
    close = prices
    # Add intra-candle noise for O/H/L
    noise_scale = base_price * 0.002  # ~0.2% noise
    open_prices = close + rng.normal(0, noise_scale * 0.3, n_candles)
    high = np.maximum(open_prices, close) + np.abs(rng.normal(0, noise_scale, n_candles))
    low = np.minimum(open_prices, close) - np.abs(rng.normal(0, noise_scale, n_candles))

    # Ensure OHLC validity: H >= max(O,C) and L <= min(O,C)
    high = np.maximum(high, np.maximum(open_prices, close))
    low = np.minimum(low, np.minimum(open_prices, close))

    # Generate spread (typical XAUUSD spread: 20-50 points)
    spread = rng.integers(20, 50, n_candles)

    # Generate tick volume
    tick_volume = rng.integers(100, 5000, n_candles)

    df = pd.DataFrame({
        "timestamp": pd.DatetimeIndex(timestamps, tz=timezone.utc),
        "open": np.round(open_prices, 2),
        "high": np.round(high, 2),
        "low": np.round(low, 2),
        "close": np.round(close, 2),
        "tick_volume": tick_volume,
        "spread": spread,
        "real_volume": np.zeros(n_candles, dtype=int),  # Usually 0 for forex/CFDs
    })

    metadata = CollectionMetadata(
        symbol=internal_symbol,
        broker_symbol="SYNTHETIC",
        timeframe=timeframe,
        start_date=start,
        end_date=end,
        row_count=len(df),
        source="SYNTHETIC — NOT FOR RESEARCH USE",
        available_fields=("timestamp", "open", "high", "low", "close", "tick_volume", "spread", "real_volume"),
        unavailable_fields=(),
    )

    logger.info(
        "Generated %d synthetic %s candles for development/testing. "
        "THIS IS NOT REAL MARKET DATA.",
        len(df), timeframe,
    )

    return df, metadata
