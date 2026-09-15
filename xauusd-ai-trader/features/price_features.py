"""
XAUUSD AI Trading Research System — Price Features

Deterministic price-derived features. Every feature has an explicit
mathematical definition. All functions are pure: (DataFrame) -> DataFrame.
No side effects, no external state, no look-ahead.

Feature definitions:
- return_1:           (close[t] - close[t-1]) / close[t-1]
- log_return_1:       ln(close[t] / close[t-1])
- rolling_return_N:   (close[t] - close[t-N]) / close[t-N]
- candle_range:       high[t] - low[t]
- candle_body:        |close[t] - open[t]|
- candle_body_signed: close[t] - open[t]  (positive = bullish)
- upper_wick:         high[t] - max(open[t], close[t])
- lower_wick:         min(open[t], close[t]) - low[t]
- rolling_volatility_N: std(return_1[t-N+1:t+1])
"""

import pandas as pd
import numpy as np


def add_returns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add simple and log returns based on close prices.

    Adds columns:
    - return_1: Simple 1-period return
    - log_return_1: Log 1-period return
    """
    df = df.copy()
    df["return_1"] = df["close"].pct_change()
    # Log return: ln(P_t / P_{t-1}), using shift to avoid look-ahead
    df["log_return_1"] = np.log(df["close"] / df["close"].shift(1))
    return df


def add_rolling_returns(df: pd.DataFrame, periods: tuple[int, ...] = (5, 10, 20)) -> pd.DataFrame:
    """
    Add rolling returns over multiple lookback periods.

    rolling_return_N = (close[t] - close[t-N]) / close[t-N]

    Only uses past data (shift by N periods).
    """
    df = df.copy()
    for n in periods:
        df[f"rolling_return_{n}"] = (df["close"] - df["close"].shift(n)) / df["close"].shift(n)
    return df


def add_candle_anatomy(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add candle structure features.

    - candle_range:       high - low (total price excursion)
    - candle_body:        |close - open| (absolute body size)
    - candle_body_signed: close - open (positive = bullish)
    - upper_wick:         high - max(open, close)
    - lower_wick:         min(open, close) - low
    """
    df = df.copy()
    df["candle_range"] = df["high"] - df["low"]
    df["candle_body"] = (df["close"] - df["open"]).abs()
    df["candle_body_signed"] = df["close"] - df["open"]
    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]
    return df


def add_rolling_volatility(df: pd.DataFrame, periods: tuple[int, ...] = (10, 20, 50)) -> pd.DataFrame:
    """
    Add rolling volatility (standard deviation of returns).

    rolling_volatility_N = std(return_1[t-N+1 : t+1])

    Requires return_1 column. Uses min_periods=N to avoid partial
    window estimates at the start of the series.
    """
    df = df.copy()
    if "return_1" not in df.columns:
        df["return_1"] = df["close"].pct_change()

    for n in periods:
        df[f"rolling_volatility_{n}"] = df["return_1"].rolling(window=n, min_periods=n).std()
    return df


def add_all_price_features(
    df: pd.DataFrame,
    rolling_return_periods: tuple[int, ...] = (5, 10, 20),
    rolling_volatility_periods: tuple[int, ...] = (10, 20, 50),
) -> pd.DataFrame:
    """
    Add all price features in a single call.

    Convenience function that applies all price feature generators.
    """
    df = add_returns(df)
    df = add_rolling_returns(df, periods=rolling_return_periods)
    df = add_candle_anatomy(df)
    df = add_rolling_volatility(df, periods=rolling_volatility_periods)
    return df
