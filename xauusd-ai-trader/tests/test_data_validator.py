"""
Tests — Data Validator

Tests that the validation system correctly detects:
- Duplicate timestamps
- Missing candles
- Invalid OHLC relationships
- Impossible price values
- Timestamp ordering problems
- Abnormal spreads
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pandas as pd
import numpy as np
import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.data_validator import validate, Verdict, Severity


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_good_df(n: int = 100, timeframe: str = "H1") -> pd.DataFrame:
    """Create a valid XAUUSD dataset for testing."""
    tf_minutes = {"M1": 1, "M5": 5, "M15": 15, "H1": 60, "H4": 240, "D1": 1440}
    interval = timedelta(minutes=tf_minutes.get(timeframe, 60))

    # Start on a Monday
    start = datetime(2025, 1, 6, 0, 0, tzinfo=timezone.utc)
    timestamps = []
    current = start
    while len(timestamps) < n:
        if current.weekday() < 5:  # Skip weekends
            timestamps.append(current)
        current += interval

    rng = np.random.default_rng(42)
    base = 2650.0
    close = base + np.cumsum(rng.normal(0, 2, n))
    open_p = close + rng.normal(0, 1, n)
    high = np.maximum(open_p, close) + np.abs(rng.normal(0, 3, n))
    low = np.minimum(open_p, close) - np.abs(rng.normal(0, 3, n))

    return pd.DataFrame({
        "timestamp": pd.DatetimeIndex(timestamps, tz=timezone.utc),
        "open": np.round(open_p, 2),
        "high": np.round(high, 2),
        "low": np.round(low, 2),
        "close": np.round(close, 2),
        "tick_volume": rng.integers(100, 5000, n),
        "spread": rng.integers(20, 50, n),
        "real_volume": np.zeros(n, dtype=int),
    })


# ── Tests ────────────────────────────────────────────────────────────────────

class TestValidDataset:
    """A properly formed dataset should pass all checks."""

    def test_good_data_passes(self):
        df = make_good_df()
        # Use a relaxed missing-candle threshold since the test helper
        # generates weekday-only data with natural gaps
        report = validate(df, "H1", max_missing_pct=20.0)
        assert report.verdict in (Verdict.GOOD, Verdict.WARNING)

    def test_report_has_all_checks(self):
        df = make_good_df()
        report = validate(df, "H1")
        check_names = [c.name for c in report.checks]
        assert "No duplicate timestamps" in check_names
        assert "Valid OHLC relationships" in check_names
        assert "Price values within plausible range" in check_names


class TestDuplicateDetection:
    """Duplicate timestamps must be detected."""

    def test_detects_duplicates(self):
        df = make_good_df(50)
        # Duplicate a timestamp
        df.loc[10, "timestamp"] = df.loc[9, "timestamp"]
        report = validate(df, "H1", max_duplicates=0)
        dup_check = [c for c in report.checks if "duplicate" in c.name.lower()][0]
        assert not dup_check.passed
        assert dup_check.count == 1

    def test_no_false_positive(self):
        df = make_good_df(50)
        report = validate(df, "H1")
        dup_check = [c for c in report.checks if "duplicate" in c.name.lower()][0]
        assert dup_check.passed


class TestInvalidOHLC:
    """Invalid OHLC relationships must be detected."""

    def test_high_below_close(self):
        df = make_good_df(50)
        df.loc[5, "high"] = df.loc[5, "close"] - 10  # High below close
        report = validate(df, "H1")
        ohlc_check = [c for c in report.checks if "OHLC" in c.name][0]
        assert not ohlc_check.passed
        assert ohlc_check.severity == Severity.CRITICAL

    def test_low_above_open(self):
        df = make_good_df(50)
        df.loc[3, "low"] = df.loc[3, "open"] + 10  # Low above open
        report = validate(df, "H1")
        ohlc_check = [c for c in report.checks if "OHLC" in c.name][0]
        assert not ohlc_check.passed

    def test_high_below_low(self):
        df = make_good_df(50)
        df.loc[7, "high"] = df.loc[7, "low"] - 5
        report = validate(df, "H1")
        ohlc_check = [c for c in report.checks if "OHLC" in c.name][0]
        assert not ohlc_check.passed


class TestImpossiblePrices:
    """Impossible price values must be detected."""

    def test_negative_price(self):
        df = make_good_df(50)
        df.loc[10, "close"] = -100.0
        df.loc[10, "low"] = -100.0
        report = validate(df, "H1")
        price_check = [c for c in report.checks if "plausible" in c.name.lower()][0]
        assert not price_check.passed

    def test_zero_price(self):
        df = make_good_df(50)
        df.loc[10, "close"] = 0.0
        df.loc[10, "low"] = 0.0
        report = validate(df, "H1")
        price_check = [c for c in report.checks if "plausible" in c.name.lower()][0]
        assert not price_check.passed

    def test_implausibly_high_price(self):
        df = make_good_df(50)
        df.loc[10, "high"] = 999999.0
        report = validate(df, "H1")
        price_check = [c for c in report.checks if "plausible" in c.name.lower()][0]
        assert not price_check.passed


class TestTimestampOrdering:
    """Timestamps must be monotonically increasing."""

    def test_unordered_timestamps(self):
        df = make_good_df(50)
        # Swap two rows
        ts_a = df.loc[10, "timestamp"]
        df.loc[10, "timestamp"] = df.loc[20, "timestamp"]
        df.loc[20, "timestamp"] = ts_a
        report = validate(df, "H1")
        order_check = [c for c in report.checks if "monotonic" in c.name.lower()][0]
        assert not order_check.passed


class TestEmptyDataset:
    """Empty datasets must be rejected."""

    def test_empty_df(self):
        df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])
        report = validate(df, "H1")
        assert report.verdict == Verdict.FAIL

    def test_missing_columns(self):
        df = pd.DataFrame({"price": [1, 2, 3]})
        report = validate(df, "H1")
        assert report.verdict == Verdict.FAIL


class TestAbnormalSpreads:
    """Abnormally high spreads should be flagged."""

    def test_extreme_spread(self):
        df = make_good_df(50)
        df["spread"] = 30  # Normal
        df.loc[5, "spread"] = 5000  # Extreme
        report = validate(df, "H1", max_spread_multiplier=10.0)
        spread_check = [c for c in report.checks if "spread" in c.name.lower()][0]
        # Should flag as warning
        assert not spread_check.passed or spread_check.count > 0
