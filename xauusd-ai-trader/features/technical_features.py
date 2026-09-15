"""
XAUUSD AI Trading Research System — Technical Features

Classical technical indicators implemented from scratch using pandas/numpy.
No TA-Lib dependency. Every indicator has an explicit mathematical definition.
All functions are pure: (DataFrame) -> DataFrame. No look-ahead.

Indicator definitions:

SMA(n):       mean(close[t-n+1 : t+1])
EMA(n):       exponential weighted mean with span=n
RSI(n):       100 - 100 / (1 + avg_gain / avg_loss)  [Wilder's smoothing]
MACD:         EMA(fast) - EMA(slow), signal = EMA(MACD, signal_period)
ATR(n):       EMA/SMA of true_range over n periods
ADX(n):       smoothed |+DI - -DI| / (+DI + -DI) * 100
Bollinger:    middle = SMA(n), upper/lower = middle ± k*std(n)
"""

import pandas as pd
import numpy as np


def add_sma(df: pd.DataFrame, periods: tuple[int, ...] = (20, 50, 200)) -> pd.DataFrame:
    """
    Add Simple Moving Averages.

    SMA(n) = mean(close[t-n+1 : t+1])
    """
    df = df.copy()
    for n in periods:
        df[f"sma_{n}"] = df["close"].rolling(window=n, min_periods=n).mean()
    return df


def add_ema(df: pd.DataFrame, periods: tuple[int, ...] = (12, 26, 50)) -> pd.DataFrame:
    """
    Add Exponential Moving Averages.

    EMA(n) uses span=n (decay factor alpha = 2/(n+1)).
    adjust=False for Wilder-compatible smoothing.
    """
    df = df.copy()
    for n in periods:
        df[f"ema_{n}"] = df["close"].ewm(span=n, adjust=False, min_periods=n).mean()
    return df


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Add Relative Strength Index (Wilder's method).

    Steps:
    1. delta = close[t] - close[t-1]
    2. gain = max(delta, 0), loss = max(-delta, 0)
    3. avg_gain = EWM(gain, alpha=1/period)
    4. avg_loss = EWM(loss, alpha=1/period)
    5. RS = avg_gain / avg_loss
    6. RSI = 100 - 100 / (1 + RS)
    """
    df = df.copy()
    delta = df["close"].diff()

    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    # Wilder's smoothing: alpha = 1/period
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    df[f"rsi_{period}"] = 100.0 - (100.0 / (1.0 + rs))

    return df


def add_macd(
    df: pd.DataFrame,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """
    Add MACD (Moving Average Convergence Divergence).

    MACD line = EMA(fast) - EMA(slow)
    Signal line = EMA(MACD, signal)
    Histogram = MACD - Signal
    """
    df = df.copy()

    ema_fast = df["close"].ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False, min_periods=slow).mean()

    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False, min_periods=signal).mean()
    df["macd_histogram"] = df["macd"] - df["macd_signal"]

    return df


def _true_range(df: pd.DataFrame) -> pd.Series:
    """
    Calculate True Range.

    TR = max(high - low, |high - prev_close|, |low - prev_close|)
    """
    prev_close = df["close"].shift(1)
    tr1 = df["high"] - df["low"]
    tr2 = (df["high"] - prev_close).abs()
    tr3 = (df["low"] - prev_close).abs()
    return pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Add Average True Range (Wilder's smoothing).

    ATR(n) = EWM(true_range, alpha=1/n)
    """
    df = df.copy()
    tr = _true_range(df)
    df[f"atr_{period}"] = tr.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    return df


def add_adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Add Average Directional Index.

    Steps:
    1. +DM = high[t] - high[t-1] if positive and > |low[t-1] - low[t]|, else 0
    2. -DM = low[t-1] - low[t] if positive and > high[t] - high[t-1], else 0
    3. Smooth +DM, -DM, TR with Wilder's EWM
    4. +DI = 100 * smoothed_+DM / smoothed_TR
    5. -DI = 100 * smoothed_-DM / smoothed_TR
    6. DX = 100 * |+DI - -DI| / (+DI + -DI)
    7. ADX = Wilder's EWM of DX
    """
    df = df.copy()

    high_diff = df["high"].diff()
    low_diff = -df["low"].diff()  # Note: negative diff means low went lower

    plus_dm = pd.Series(np.where(
        (high_diff > low_diff) & (high_diff > 0),
        high_diff,
        0.0,
    ), index=df.index)

    minus_dm = pd.Series(np.where(
        (low_diff > high_diff) & (low_diff > 0),
        low_diff,
        0.0,
    ), index=df.index)

    tr = _true_range(df)

    # Wilder's smoothing
    alpha = 1.0 / period
    smoothed_tr = tr.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    smoothed_plus_dm = plus_dm.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    smoothed_minus_dm = minus_dm.ewm(alpha=alpha, min_periods=period, adjust=False).mean()

    # Directional indicators
    plus_di = 100.0 * smoothed_plus_dm / smoothed_tr.replace(0, np.nan)
    minus_di = 100.0 * smoothed_minus_dm / smoothed_tr.replace(0, np.nan)

    # DX and ADX
    di_sum = plus_di + minus_di
    dx = 100.0 * (plus_di - minus_di).abs() / di_sum.replace(0, np.nan)
    adx = dx.ewm(alpha=alpha, min_periods=period, adjust=False).mean()

    df[f"plus_di_{period}"] = plus_di
    df[f"minus_di_{period}"] = minus_di
    df[f"adx_{period}"] = adx

    return df


def add_bollinger_bands(df: pd.DataFrame, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """
    Add Bollinger Bands.

    middle = SMA(close, period)
    upper  = middle + num_std * std(close, period)
    lower  = middle - num_std * std(close, period)
    %B     = (close - lower) / (upper - lower)
    bandwidth = (upper - lower) / middle
    """
    df = df.copy()

    middle = df["close"].rolling(window=period, min_periods=period).mean()
    std = df["close"].rolling(window=period, min_periods=period).std()

    df[f"bb_middle_{period}"] = middle
    df[f"bb_upper_{period}"] = middle + num_std * std
    df[f"bb_lower_{period}"] = middle - num_std * std

    band_width = df[f"bb_upper_{period}"] - df[f"bb_lower_{period}"]
    df[f"bb_pct_b_{period}"] = (df["close"] - df[f"bb_lower_{period}"]) / band_width.replace(0, np.nan)
    df[f"bb_bandwidth_{period}"] = band_width / middle.replace(0, np.nan)

    return df


def add_all_technical_features(
    df: pd.DataFrame,
    sma_periods: tuple[int, ...] = (20, 50, 200),
    ema_periods: tuple[int, ...] = (12, 26, 50),
    rsi_period: int = 14,
    macd_fast: int = 12,
    macd_slow: int = 26,
    macd_signal: int = 9,
    atr_period: int = 14,
    adx_period: int = 14,
    bollinger_period: int = 20,
    bollinger_std: float = 2.0,
) -> pd.DataFrame:
    """Add all technical features in a single call."""
    df = add_sma(df, periods=sma_periods)
    df = add_ema(df, periods=ema_periods)
    df = add_rsi(df, period=rsi_period)
    df = add_macd(df, fast=macd_fast, slow=macd_slow, signal=macd_signal)
    df = add_atr(df, period=atr_period)
    df = add_adx(df, period=adx_period)
    df = add_bollinger_bands(df, period=bollinger_period, num_std=bollinger_std)
    return df
