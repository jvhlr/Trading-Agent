"""
Tests — Structure Features

Tests swing detection, HH/HL/LH/LL patterns, session levels,
and trend classification.
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from features.structure_features import (
    detect_swings,
    add_swing_patterns,
    add_session_levels,
    classify_trend,
    add_all_structure_features,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_swinging_df(n: int = 60) -> pd.DataFrame:
    """Create data with clear swing points."""
    # Create a sine-wave-like pattern for clear swings
    t = np.arange(n)
    close = 2650 + 20 * np.sin(2 * np.pi * t / 20)  # Period of 20 bars
    open_p = close + np.random.default_rng(42).normal(0, 1, n)
    high = np.maximum(open_p, close) + 3
    low = np.minimum(open_p, close) - 3

    start = datetime(2025, 1, 6, 0, 0, tzinfo=timezone.utc)
    timestamps = [start + timedelta(hours=i) for i in range(n)]

    return pd.DataFrame({
        "timestamp": pd.DatetimeIndex(timestamps, tz=timezone.utc),
        "open": np.round(open_p, 2),
        "high": np.round(high, 2),
        "low": np.round(low, 2),
        "close": np.round(close, 2),
    })


def make_uptrend_df(n: int = 100) -> pd.DataFrame:
    """Create a clear uptrend dataset."""
    rng = np.random.default_rng(42)
    close = 2600 + np.arange(n) * 1.0 + rng.normal(0, 0.5, n)
    open_p = close + rng.normal(0, 0.3, n)
    high = np.maximum(open_p, close) + 2
    low = np.minimum(open_p, close) - 2

    start = datetime(2025, 1, 6, 0, 0, tzinfo=timezone.utc)
    timestamps = [start + timedelta(hours=i) for i in range(n)]

    return pd.DataFrame({
        "timestamp": pd.DatetimeIndex(timestamps, tz=timezone.utc),
        "open": np.round(open_p, 2),
        "high": np.round(high, 2),
        "low": np.round(low, 2),
        "close": np.round(close, 2),
    })


# ── Tests ────────────────────────────────────────────────────────────────────

class TestSwingDetection:
    """Test swing high/low detection."""

    def test_swings_detected(self):
        df = make_swinging_df()
        result = detect_swings(df, lookback=5)
        assert result["swing_high"].any(), "Should detect at least one swing high"
        assert result["swing_low"].any(), "Should detect at least one swing low"

    def test_swing_high_is_local_max(self):
        df = make_swinging_df()
        result = detect_swings(df, lookback=5)
        for idx in result.index[result["swing_high"]]:
            # The swing high price should be >= nearby highs
            start = max(0, idx - 5)
            end = min(len(df), idx + 6)
            local_highs = result["high"].iloc[start:end]
            assert result["high"].iloc[idx] == local_highs.max()

    def test_swing_low_is_local_min(self):
        df = make_swinging_df()
        result = detect_swings(df, lookback=5)
        for idx in result.index[result["swing_low"]]:
            start = max(0, idx - 5)
            end = min(len(df), idx + 6)
            local_lows = result["low"].iloc[start:end]
            assert result["low"].iloc[idx] == local_lows.min()

    def test_no_swings_at_edges(self):
        """First and last `lookback` bars should not have swings."""
        df = make_swinging_df()
        result = detect_swings(df, lookback=5)
        assert not result["swing_high"].iloc[:5].any()
        assert not result["swing_low"].iloc[:5].any()
        assert not result["swing_high"].iloc[-5:].any()
        assert not result["swing_low"].iloc[-5:].any()


class TestSwingPatterns:
    """Test HH/HL/LH/LL classification."""

    def test_patterns_exist(self):
        df = make_swinging_df(80)
        df = detect_swings(df, lookback=5)
        result = add_swing_patterns(df)
        # Should have at least some patterns classified
        has_high_pattern = result["swing_pattern_high"].notna().any()
        has_low_pattern = result["swing_pattern_low"].notna().any()
        assert has_high_pattern or has_low_pattern

    def test_requires_swings_first(self):
        df = make_swinging_df()
        with pytest.raises(ValueError, match="detect_swings"):
            add_swing_patterns(df)


class TestSessionLevels:
    """Test previous daily session high/low."""

    def test_prev_day_levels(self):
        df = make_uptrend_df(72)  # 3 days of H1 data
        result = add_session_levels(df)
        assert "prev_day_high" in result.columns
        assert "prev_day_low" in result.columns
        # First day should have NaN prev levels
        first_day = result["timestamp"].dt.date.iloc[0]
        first_day_rows = result[result["timestamp"].dt.date == first_day]
        assert first_day_rows["prev_day_high"].isna().all()

    def test_requires_timestamp(self):
        df = pd.DataFrame({"open": [1], "high": [2], "low": [0.5], "close": [1.5]})
        with pytest.raises(ValueError, match="timestamp"):
            add_session_levels(df)


class TestTrendClassification:
    """Test simple SMA-based trend classification."""

    def test_uptrend_classified(self):
        df = make_uptrend_df(100)
        result = classify_trend(df, sma_period=20)
        # Last bars should be BULLISH in a clear uptrend
        recent_trends = result["trend"].tail(20)
        bullish_pct = (recent_trends == "BULLISH").mean()
        assert bullish_pct > 0.5

    def test_trend_values(self):
        df = make_uptrend_df(50)
        result = classify_trend(df, sma_period=20)
        valid_values = {"BULLISH", "BEARISH", "NEUTRAL"}
        assert set(result["trend"].unique()).issubset(valid_values)


class TestAllStructureFeatures:
    """Test the convenience function."""

    def test_adds_all_columns(self):
        df = make_swinging_df(80)
        result = add_all_structure_features(df)
        expected = ["swing_high", "swing_low", "prev_day_high", "prev_day_low", "trend"]
        for col in expected:
            assert col in result.columns, f"Missing: {col}"
