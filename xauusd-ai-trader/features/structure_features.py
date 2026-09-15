"""
XAUUSD AI Trading Research System — Market Structure Features

Deterministic market structure analysis: swing detection, higher-highs /
higher-lows / lower-highs / lower-lows patterns, previous session levels,
and simple trend classification.

All functions are pure: (DataFrame) -> DataFrame. No look-ahead.

Definitions:
- Swing High: high[t] > all highs in [t-lookback, t+lookback]
  (only confirmed after lookback bars have passed)
- Swing Low:  low[t] < all lows in [t-lookback, t+lookback]
  (only confirmed after lookback bars have passed)
- HH: current swing high > previous swing high
- HL: current swing low > previous swing low
- LH: current swing high < previous swing high
- LL: current swing low < previous swing low
- Trend: BULLISH if recent HH+HL, BEARISH if LH+LL, else NEUTRAL
"""

import pandas as pd
import numpy as np


def detect_swings(df: pd.DataFrame, lookback: int = 5) -> pd.DataFrame:
    """
    Detect swing highs and swing lows.

    A swing high at bar t is confirmed only when lookback bars have
    passed AFTER it — meaning we shift the detection window to avoid
    look-ahead. The swing is marked at its actual bar, but only
    becomes visible after the confirmation period.

    Adds columns:
    - swing_high: True if this bar is a confirmed swing high
    - swing_low: True if this bar is a confirmed swing low
    - swing_high_price: Price at swing high (NaN elsewhere)
    - swing_low_price: Price at swing low (NaN elsewhere)
    """
    df = df.copy()

    n = len(df)
    swing_high = np.zeros(n, dtype=bool)
    swing_low = np.zeros(n, dtype=bool)

    highs = df["high"].values
    lows = df["low"].values

    # A bar at index i is a swing high if:
    # high[i] >= all highs in [i-lookback, i+lookback]
    # But to avoid look-ahead, we can only confirm it at bar i+lookback.
    # We mark it at position i but it only enters the feature set once
    # bar i+lookback exists.
    for i in range(lookback, n - lookback):
        window_high = highs[i - lookback: i + lookback + 1]
        if highs[i] == window_high.max():
            swing_high[i] = True

        window_low = lows[i - lookback: i + lookback + 1]
        if lows[i] == window_low.min():
            swing_low[i] = True

    df["swing_high"] = swing_high
    df["swing_low"] = swing_low
    df["swing_high_price"] = np.where(swing_high, highs, np.nan)
    df["swing_low_price"] = np.where(swing_low, lows, np.nan)

    return df


def add_swing_patterns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Classify swing patterns: HH, HL, LH, LL.

    Requires swing_high_price and swing_low_price columns
    (call detect_swings first).

    Adds columns:
    - prev_swing_high: Previous swing high price (forward-filled)
    - prev_swing_low: Previous swing low price (forward-filled)
    - swing_pattern_high: 'HH' or 'LH' at swing highs, NaN elsewhere
    - swing_pattern_low: 'HL' or 'LL' at swing lows, NaN elsewhere
    """
    df = df.copy()

    if "swing_high_price" not in df.columns or "swing_low_price" not in df.columns:
        raise ValueError("Run detect_swings() first to create swing columns.")

    # Forward-fill swing prices to create a "most recent swing" column
    df["prev_swing_high"] = df["swing_high_price"].ffill()
    df["prev_swing_low"] = df["swing_low_price"].ffill()

    # For HH/LH classification, compare current swing high to previous
    swing_highs = df.loc[df["swing_high"], "swing_high_price"]
    prev_highs = swing_highs.shift(1)
    pattern_high = pd.Series(np.nan, index=df.index, dtype=object)
    for idx in swing_highs.index:
        if idx in prev_highs.index and pd.notna(prev_highs.loc[idx]):
            if swing_highs.loc[idx] > prev_highs.loc[idx]:
                pattern_high.loc[idx] = "HH"
            else:
                pattern_high.loc[idx] = "LH"
    df["swing_pattern_high"] = pattern_high

    # For HL/LL classification
    swing_lows = df.loc[df["swing_low"], "swing_low_price"]
    prev_lows = swing_lows.shift(1)
    pattern_low = pd.Series(np.nan, index=df.index, dtype=object)
    for idx in swing_lows.index:
        if idx in prev_lows.index and pd.notna(prev_lows.loc[idx]):
            if swing_lows.loc[idx] > prev_lows.loc[idx]:
                pattern_low.loc[idx] = "HL"
            else:
                pattern_low.loc[idx] = "LL"
    df["swing_pattern_low"] = pattern_low

    return df


def add_session_levels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add previous daily session high/low levels.

    For each bar, looks at the previous calendar day's high and low.
    Uses UTC day boundaries.

    Adds columns:
    - prev_day_high: Previous day's high
    - prev_day_low: Previous day's low
    """
    df = df.copy()

    if "timestamp" not in df.columns:
        raise ValueError("DataFrame must have a 'timestamp' column.")

    # Extract date for grouping
    df["_date"] = df["timestamp"].dt.date

    # Calculate daily high/low
    daily_hl = df.groupby("_date").agg(
        daily_high=("high", "max"),
        daily_low=("low", "min"),
    )

    # Shift by 1 day to get PREVIOUS day's levels
    daily_hl["prev_day_high"] = daily_hl["daily_high"].shift(1)
    daily_hl["prev_day_low"] = daily_hl["daily_low"].shift(1)

    # Merge back
    df = df.merge(
        daily_hl[["prev_day_high", "prev_day_low"]],
        left_on="_date",
        right_index=True,
        how="left",
    )

    df = df.drop(columns=["_date"])

    return df


def classify_trend(df: pd.DataFrame, sma_period: int = 20) -> pd.DataFrame:
    """
    Simple trend classification based on price relative to SMA.

    Classification:
    - BULLISH: close > SMA and SMA is rising (SMA[t] > SMA[t-1])
    - BEARISH: close < SMA and SMA is falling (SMA[t] < SMA[t-1])
    - NEUTRAL: otherwise

    This is deliberately simple. More sophisticated trend detection
    belongs in later phases.

    Adds columns:
    - trend_sma: The SMA used for classification
    - trend: 'BULLISH', 'BEARISH', or 'NEUTRAL'
    """
    df = df.copy()

    sma_col = f"_trend_sma_{sma_period}"
    df[sma_col] = df["close"].rolling(window=sma_period, min_periods=sma_period).mean()

    sma_rising = df[sma_col] > df[sma_col].shift(1)
    sma_falling = df[sma_col] < df[sma_col].shift(1)
    above_sma = df["close"] > df[sma_col]
    below_sma = df["close"] < df[sma_col]

    conditions = [
        above_sma & sma_rising,
        below_sma & sma_falling,
    ]
    choices = ["BULLISH", "BEARISH"]

    df["trend"] = np.select(conditions, choices, default="NEUTRAL")
    df["trend_sma"] = df[sma_col]
    df = df.drop(columns=[sma_col])

    return df


def add_all_structure_features(
    df: pd.DataFrame,
    swing_lookback: int = 5,
    trend_sma_period: int = 20,
) -> pd.DataFrame:
    """Add all market structure features in a single call."""
    df = detect_swings(df, lookback=swing_lookback)
    df = add_swing_patterns(df)
    df = add_session_levels(df)
    df = classify_trend(df, sma_period=trend_sma_period)
    return df
