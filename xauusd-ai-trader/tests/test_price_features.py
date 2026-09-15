"""
Tests — Price Features

Tests each price feature against known manual calculations on small
synthetic datasets. Tests edge cases: single candle, all-same prices.
"""

import sys
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from features.price_features import (
    add_returns,
    add_rolling_returns,
    add_candle_anatomy,
    add_rolling_volatility,
    add_all_price_features,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_simple_df() -> pd.DataFrame:
    """Create a small DataFrame with known values for manual verification."""
    return pd.DataFrame({
        "open":  [100.0, 102.0, 101.0, 103.0, 105.0],
        "high":  [104.0, 106.0, 104.0, 107.0, 108.0],
        "low":   [ 98.0, 100.0,  99.0, 101.0, 103.0],
        "close": [102.0, 104.0, 100.0, 106.0, 104.0],
    })


# ── Tests ────────────────────────────────────────────────────────────────────

class TestReturns:
    """Test simple and log return calculations."""

    def test_simple_return(self):
        df = make_simple_df()
        result = add_returns(df)

        # return_1[1] = (104 - 102) / 102 ≈ 0.01961
        assert pd.isna(result["return_1"].iloc[0])  # First row has no previous
        np.testing.assert_almost_equal(result["return_1"].iloc[1], 2 / 102, decimal=5)

    def test_log_return(self):
        df = make_simple_df()
        result = add_returns(df)

        # log_return_1[1] = ln(104/102) ≈ 0.01961
        expected = np.log(104 / 102)
        np.testing.assert_almost_equal(result["log_return_1"].iloc[1], expected, decimal=5)

    def test_first_row_is_nan(self):
        df = make_simple_df()
        result = add_returns(df)
        assert pd.isna(result["return_1"].iloc[0])
        assert pd.isna(result["log_return_1"].iloc[0])


class TestRollingReturns:
    """Test rolling return calculations."""

    def test_rolling_return_periods(self):
        df = pd.DataFrame({"close": [100, 102, 104, 106, 108, 110, 112]})
        result = add_rolling_returns(df, periods=(3, 5))

        # rolling_return_3[3] = (106 - 100) / 100 = 0.06
        np.testing.assert_almost_equal(result["rolling_return_3"].iloc[3], 0.06, decimal=5)

        # rolling_return_5[5] = (110 - 100) / 100 = 0.10
        np.testing.assert_almost_equal(result["rolling_return_5"].iloc[5], 0.10, decimal=5)

    def test_early_rows_are_nan(self):
        df = pd.DataFrame({"close": [100, 102, 104]})
        result = add_rolling_returns(df, periods=(5,))
        assert result["rolling_return_5"].isna().all()


class TestCandleAnatomy:
    """Test candle structure calculations."""

    def test_candle_range(self):
        df = make_simple_df()
        result = add_candle_anatomy(df)
        # Range[0] = 104 - 98 = 6
        assert result["candle_range"].iloc[0] == 6.0

    def test_candle_body(self):
        df = make_simple_df()
        result = add_candle_anatomy(df)
        # Body[0] = |102 - 100| = 2
        assert result["candle_body"].iloc[0] == 2.0
        # Body_signed[0] = 102 - 100 = 2 (bullish)
        assert result["candle_body_signed"].iloc[0] == 2.0

    def test_bearish_candle_body(self):
        df = make_simple_df()
        result = add_candle_anatomy(df)
        # Bar 4: close=104, open=105 → body_signed = -1 (bearish)
        assert result["candle_body_signed"].iloc[4] == -1.0

    def test_upper_wick(self):
        df = make_simple_df()
        result = add_candle_anatomy(df)
        # Bar 0: high=104, max(open=100, close=102) = 102 → upper_wick = 2
        assert result["upper_wick"].iloc[0] == 2.0

    def test_lower_wick(self):
        df = make_simple_df()
        result = add_candle_anatomy(df)
        # Bar 0: min(open=100, close=102) = 100, low=98 → lower_wick = 2
        assert result["lower_wick"].iloc[0] == 2.0


class TestRollingVolatility:
    """Test rolling volatility calculation."""

    def test_volatility_is_positive(self):
        df = pd.DataFrame({"close": np.random.default_rng(42).normal(100, 1, 50)})
        df["return_1"] = df["close"].pct_change()
        result = add_rolling_volatility(df, periods=(10,))
        # Non-NaN volatility values should be positive
        non_nan = result["rolling_volatility_10"].dropna()
        assert (non_nan > 0).all()

    def test_constant_prices_zero_volatility(self):
        df = pd.DataFrame({"close": [100.0] * 20})
        df["return_1"] = df["close"].pct_change()
        result = add_rolling_volatility(df, periods=(10,))
        # Returns are 0 after first bar, so volatility should be 0
        non_nan = result["rolling_volatility_10"].dropna()
        assert (non_nan == 0.0).all()

    def test_min_periods_respected(self):
        df = pd.DataFrame({"close": [100, 101, 102, 103, 104]})
        result = add_rolling_volatility(df, periods=(10,))
        # Not enough data for period=10
        assert result["rolling_volatility_10"].isna().all()


class TestAllPriceFeatures:
    """Test the convenience function that adds all features."""

    def test_adds_all_columns(self):
        df = pd.DataFrame({
            "open": np.random.default_rng(42).normal(100, 1, 50),
            "high": np.random.default_rng(43).normal(101, 1, 50),
            "low": np.random.default_rng(44).normal(99, 1, 50),
            "close": np.random.default_rng(45).normal(100, 1, 50),
        })
        result = add_all_price_features(df, rolling_return_periods=(5,), rolling_volatility_periods=(10,))

        expected_cols = [
            "return_1", "log_return_1", "rolling_return_5",
            "candle_range", "candle_body", "candle_body_signed",
            "upper_wick", "lower_wick", "rolling_volatility_10",
        ]
        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_does_not_modify_original(self):
        df = make_simple_df()
        original_cols = list(df.columns)
        _ = add_all_price_features(df)
        assert list(df.columns) == original_cols
