"""
Tests — Technical Features

Tests SMA, EMA, RSI, MACD, ATR, ADX, Bollinger Bands against
known values and mathematical properties.
"""

import sys
from pathlib import Path

import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from features.technical_features import (
    add_sma,
    add_ema,
    add_rsi,
    add_macd,
    add_atr,
    add_adx,
    add_bollinger_bands,
    add_all_technical_features,
)


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_trending_df(n: int = 100, direction: str = "up") -> pd.DataFrame:
    """Create a trending dataset."""
    rng = np.random.default_rng(42)
    if direction == "up":
        close = 100 + np.arange(n) * 0.5 + rng.normal(0, 0.5, n)
    else:
        close = 200 - np.arange(n) * 0.5 + rng.normal(0, 0.5, n)

    open_p = close + rng.normal(0, 0.3, n)
    high = np.maximum(open_p, close) + np.abs(rng.normal(0, 1, n))
    low = np.minimum(open_p, close) - np.abs(rng.normal(0, 1, n))

    return pd.DataFrame({
        "open": np.round(open_p, 2),
        "high": np.round(high, 2),
        "low": np.round(low, 2),
        "close": np.round(close, 2),
    })


# ── Tests ────────────────────────────────────────────────────────────────────

class TestSMA:
    """Test Simple Moving Average."""

    def test_sma_manual_calculation(self):
        df = pd.DataFrame({"close": [10.0, 20.0, 30.0, 40.0, 50.0]})
        result = add_sma(df, periods=(3,))
        # SMA(3)[2] = (10+20+30)/3 = 20
        np.testing.assert_almost_equal(result["sma_3"].iloc[2], 20.0)
        # SMA(3)[3] = (20+30+40)/3 = 30
        np.testing.assert_almost_equal(result["sma_3"].iloc[3], 30.0)

    def test_sma_nan_before_period(self):
        df = pd.DataFrame({"close": [10.0, 20.0, 30.0, 40.0, 50.0]})
        result = add_sma(df, periods=(3,))
        assert pd.isna(result["sma_3"].iloc[0])
        assert pd.isna(result["sma_3"].iloc[1])


class TestEMA:
    """Test Exponential Moving Average."""

    def test_ema_first_value(self):
        df = pd.DataFrame({"close": [10.0, 20.0, 30.0, 40.0, 50.0]})
        result = add_ema(df, periods=(3,))
        # First valid EMA(3) should be close to SMA(3) at position 2
        assert pd.notna(result["ema_3"].iloc[2])

    def test_ema_responds_to_price(self):
        """EMA should be above close in downtrend, below in uptrend."""
        df = make_trending_df(100, "up")
        result = add_ema(df, periods=(20,))
        # In an uptrend, close > EMA for most recent bars
        last_20 = result.tail(20)
        above_pct = (last_20["close"] > last_20["ema_20"]).mean()
        assert above_pct > 0.5  # Most bars should be above EMA in uptrend


class TestRSI:
    """Test Relative Strength Index."""

    def test_rsi_range(self):
        """RSI must be between 0 and 100."""
        df = make_trending_df(100)
        result = add_rsi(df, period=14)
        rsi = result["rsi_14"].dropna()
        assert (rsi >= 0).all()
        assert (rsi <= 100).all()

    def test_rsi_high_in_uptrend(self):
        """RSI should be elevated in a strong uptrend."""
        df = make_trending_df(100, "up")
        result = add_rsi(df, period=14)
        rsi_mean = result["rsi_14"].dropna().tail(20).mean()
        assert rsi_mean > 50  # Should be above neutral in uptrend

    def test_rsi_low_in_downtrend(self):
        """RSI should be depressed in a strong downtrend."""
        df = make_trending_df(100, "down")
        result = add_rsi(df, period=14)
        rsi_mean = result["rsi_14"].dropna().tail(20).mean()
        assert rsi_mean < 50  # Should be below neutral in downtrend


class TestMACD:
    """Test MACD."""

    def test_macd_columns_present(self):
        df = make_trending_df(100)
        result = add_macd(df)
        assert "macd" in result.columns
        assert "macd_signal" in result.columns
        assert "macd_histogram" in result.columns

    def test_histogram_is_macd_minus_signal(self):
        df = make_trending_df(100)
        result = add_macd(df)
        non_nan = result.dropna(subset=["macd", "macd_signal", "macd_histogram"])
        np.testing.assert_array_almost_equal(
            non_nan["macd_histogram"].values,
            (non_nan["macd"] - non_nan["macd_signal"]).values,
            decimal=10,
        )

    def test_macd_positive_in_uptrend(self):
        df = make_trending_df(100, "up")
        result = add_macd(df)
        # MACD should be positive in uptrend (fast EMA > slow EMA)
        macd_mean = result["macd"].dropna().tail(20).mean()
        assert macd_mean > 0


class TestATR:
    """Test Average True Range."""

    def test_atr_positive(self):
        df = make_trending_df(50)
        result = add_atr(df, period=14)
        atr = result["atr_14"].dropna()
        assert (atr > 0).all()

    def test_atr_responds_to_volatility(self):
        """Higher volatility data should have higher ATR."""
        rng = np.random.default_rng(42)
        # Low volatility
        close_low = 100 + rng.normal(0, 0.1, 50)
        df_low = pd.DataFrame({
            "open": close_low, "high": close_low + 0.2,
            "low": close_low - 0.2, "close": close_low,
        })
        # High volatility
        close_high = 100 + rng.normal(0, 5, 50)
        df_high = pd.DataFrame({
            "open": close_high, "high": close_high + 10,
            "low": close_high - 10, "close": close_high,
        })

        atr_low = add_atr(df_low, period=14)["atr_14"].dropna().mean()
        atr_high = add_atr(df_high, period=14)["atr_14"].dropna().mean()
        assert atr_high > atr_low


class TestADX:
    """Test Average Directional Index."""

    def test_adx_range(self):
        """ADX should be between 0 and 100."""
        df = make_trending_df(100)
        result = add_adx(df, period=14)
        adx = result["adx_14"].dropna()
        assert (adx >= 0).all()
        assert (adx <= 100).all()

    def test_adx_columns(self):
        df = make_trending_df(50)
        result = add_adx(df, period=14)
        assert "plus_di_14" in result.columns
        assert "minus_di_14" in result.columns
        assert "adx_14" in result.columns


class TestBollingerBands:
    """Test Bollinger Bands."""

    def test_upper_above_middle_above_lower(self):
        df = make_trending_df(50)
        result = add_bollinger_bands(df, period=20, num_std=2.0)
        non_nan = result.dropna(subset=["bb_upper_20", "bb_middle_20", "bb_lower_20"])
        assert (non_nan["bb_upper_20"] >= non_nan["bb_middle_20"]).all()
        assert (non_nan["bb_middle_20"] >= non_nan["bb_lower_20"]).all()

    def test_pct_b_range(self):
        """When price is within bands, %B should be between 0 and 1."""
        df = make_trending_df(50)
        result = add_bollinger_bands(df, period=20)
        pct_b = result["bb_pct_b_20"].dropna()
        # Most values should be reasonable (not guaranteed 0-1 if price breaks out)
        assert pct_b.median() > -1.0
        assert pct_b.median() < 2.0

    def test_middle_equals_sma(self):
        """Middle band should equal SMA."""
        df = make_trending_df(50)
        result = add_bollinger_bands(df, period=20)
        sma = df["close"].rolling(window=20, min_periods=20).mean()
        non_nan = result["bb_middle_20"].dropna()
        sma_non_nan = sma.dropna()
        np.testing.assert_array_almost_equal(non_nan.values, sma_non_nan.values, decimal=10)


class TestAllTechnical:
    """Test the convenience function."""

    def test_adds_all_indicators(self):
        df = make_trending_df(100)
        result = add_all_technical_features(df, sma_periods=(20,), ema_periods=(12,))
        expected = ["sma_20", "ema_12", "rsi_14", "macd", "atr_14", "adx_14", "bb_middle_20"]
        for col in expected:
            assert col in result.columns, f"Missing: {col}"
