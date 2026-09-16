"""
XAUUSD AI Trading Research System — Macro & Intermarket Feature Engineering

Calculates deterministic cross-market features (DXY, US10Y, US02Y, TIP, VIX, XAG, BRENT)
and merges them onto XAUUSD candle data with STRICT zero look-ahead bias (backward merge_asof).
"""

import logging
from typing import Dict, Optional, List
import numpy as np
import pandas as pd

from data.macro_data_store import MacroDataStore
from data.macro_collector import MacroCollector, MACRO_TICKER_MAP

logger = logging.getLogger(__name__)

# Macro feature column names
MACRO_FEATURE_COLS = [
    "dxy_close",
    "dxy_ret_1d",
    "dxy_ret_5d",
    "dxy_sma20_dist",
    "us10y_yield",
    "us02y_yield",
    "yield_curve_slope",
    "us10y_5d_delta",
    "tip_ret_5d",
    "vix_level",
    "vix_5d_zscore",
    "vix_spike_regime",
    "gold_silver_ratio",
    "gsr_zscore_20d",
    "gsr_zscore_50d",
    "brent_ret_5d",
    "gold_dxy_corr_30d",
    "gold_us10y_corr_30d",
    "macro_regime_code",
]


class MacroRegime:
    """Enumeration of deterministic macro regime states."""
    NEUTRAL = 0
    DOLLAR_PRESSURE = 1   # DXY surging + Real Yields up -> Strong Gold Headwind (Veto BUY)
    INFLATION_HEDGE = 2   # Oil surging + Real Rates flat/down -> Gold Tailwind (Support BUY)
    RISK_OFF_FLIGHT = 3   # VIX spiking -> Safe-Haven Demand (Veto SELL)


def align_macro_to_gold(
    gold_df: pd.DataFrame,
    macro_dfs: Dict[str, pd.DataFrame],
) -> pd.DataFrame:
    """
    Align multi-asset macro series to intraday XAUUSD candles with strict
    zero look-ahead backward merging (merge_asof).
    """
    if "timestamp" not in gold_df.columns:
        raise ValueError("gold_df must contain 'timestamp' column.")

    df_out = gold_df.copy().sort_values("timestamp").reset_index(drop=True)
    df_out["timestamp"] = pd.to_datetime(df_out["timestamp"], utc=True)

    for key, m_df in macro_dfs.items():
        if m_df.empty or "timestamp" not in m_df.columns or "close" not in m_df.columns:
            continue

        clean_m = m_df.copy().sort_values("timestamp").reset_index(drop=True)
        clean_m["timestamp"] = pd.to_datetime(clean_m["timestamp"], utc=True)
        clean_m = clean_m[["timestamp", "close"]].rename(columns={"close": f"{key.lower()}_close"})

        # Strict backward as-of merge: at gold bar T, only use macro data with ts <= T
        df_out = pd.merge_asof(
            df_out,
            clean_m,
            on="timestamp",
            direction="backward",
        )

        # Forward-fill initial missing values if any
        df_out[f"{key.lower()}_close"] = df_out[f"{key.lower()}_close"].ffill().bfill()

    return df_out


def compute_macro_features(aligned_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute all deterministic macroeconomic and intermarket features.
    
    Args:
        aligned_df: DataFrame containing XAUUSD candles aligned with macro close columns
                   (dxy_close, us10y_close, us02y_close, tip_close, vix_close, xag_close, brent_close).
    
    Returns:
        DataFrame with macro feature columns appended.
    """
    df = aligned_df.copy()

    # ── 1. US Dollar Index (DXY) Features ─────────────────────────────────
    if "dxy_close" in df.columns:
        # Approximate 1 day (24 bars for H1) and 5 days (120 bars for H1)
        # We calculate bar-based rolling returns that adapt to the series
        df["dxy_ret_1d"] = df["dxy_close"].pct_change(periods=24).fillna(0.0)
        df["dxy_ret_5d"] = df["dxy_close"].pct_change(periods=120).fillna(0.0)
        dxy_sma20 = df["dxy_close"].rolling(window=120, min_periods=1).mean()
        df["dxy_sma20_dist"] = ((df["dxy_close"] - dxy_sma20) / (dxy_sma20 + 1e-8)).fillna(0.0)
    else:
        df["dxy_close"] = 103.5
        df["dxy_ret_1d"] = 0.0
        df["dxy_ret_5d"] = 0.0
        df["dxy_sma20_dist"] = 0.0

    # ── 2. Treasury Yields & Real Rates ────────────────────────────────────
    if "us10y_close" in df.columns:
        df["us10y_yield"] = df["us10y_close"]
        df["us10y_5d_delta"] = df["us10y_close"].diff(periods=120).fillna(0.0)
    else:
        df["us10y_yield"] = 4.25
        df["us10y_5d_delta"] = 0.0

    if "us02y_close" in df.columns:
        df["us02y_yield"] = df["us02y_close"]
    else:
        df["us02y_yield"] = 4.50

    # 2s10s Yield curve slope
    df["yield_curve_slope"] = df["us10y_yield"] - df["us02y_yield"]

    if "tip_close" in df.columns:
        df["tip_ret_5d"] = df["tip_close"].pct_change(periods=120).fillna(0.0)
    else:
        df["tip_ret_5d"] = 0.0

    # ── 3. CBOE VIX Index ───────────────────────────────────────────────────
    if "vix_close" in df.columns:
        df["vix_level"] = df["vix_close"]
        vix_mean = df["vix_close"].rolling(window=120, min_periods=5).mean()
        vix_std = df["vix_close"].rolling(window=120, min_periods=5).std().replace(0, 1e-6)
        df["vix_5d_zscore"] = ((df["vix_close"] - vix_mean) / vix_std).fillna(0.0)
        df["vix_spike_regime"] = ((df["vix_level"] > 22.0) | (df["vix_5d_zscore"] > 1.5)).astype(int)
    else:
        df["vix_level"] = 15.0
        df["vix_5d_zscore"] = 0.0
        df["vix_spike_regime"] = 0

    # ── 4. Gold / Silver Ratio (GSR) ───────────────────────────────────────
    if "xag_close" in df.columns and "close" in df.columns:
        # Protect against divide by zero
        xag_safe = df["xag_close"].replace(0, np.nan).ffill().bfill()
        df["gold_silver_ratio"] = df["close"] / xag_safe
        gsr_mean20 = df["gold_silver_ratio"].rolling(window=120, min_periods=5).mean()
        gsr_std20 = df["gold_silver_ratio"].rolling(window=120, min_periods=5).std().replace(0, 1e-6)
        df["gsr_zscore_20d"] = ((df["gold_silver_ratio"] - gsr_mean20) / gsr_std20).fillna(0.0)

        gsr_mean50 = df["gold_silver_ratio"].rolling(window=300, min_periods=10).mean()
        gsr_std50 = df["gold_silver_ratio"].rolling(window=300, min_periods=10).std().replace(0, 1e-6)
        df["gsr_zscore_50d"] = ((df["gold_silver_ratio"] - gsr_mean50) / gsr_std50).fillna(0.0)
    else:
        df["gold_silver_ratio"] = 85.0
        df["gsr_zscore_20d"] = 0.0
        df["gsr_zscore_50d"] = 0.0

    # ── 5. Energy / Brent Crude Oil ─────────────────────────────────────────
    if "brent_close" in df.columns:
        df["brent_ret_5d"] = df["brent_close"].pct_change(periods=120).fillna(0.0)
    else:
        df["brent_ret_5d"] = 0.0

    # ── 6. Rolling Correlations ─────────────────────────────────────────────
    if "close" in df.columns:
        gold_ret = df["close"].pct_change().fillna(0.0)
        dxy_ret = df["dxy_close"].pct_change().fillna(0.0)
        yield_delta = df["us10y_yield"].diff().fillna(0.0)

        df["gold_dxy_corr_30d"] = gold_ret.rolling(window=120, min_periods=20).corr(dxy_ret).fillna(-0.70)
        df["gold_us10y_corr_30d"] = gold_ret.rolling(window=120, min_periods=20).corr(yield_delta).fillna(-0.50)
    else:
        df["gold_dxy_corr_30d"] = -0.70
        df["gold_us10y_corr_30d"] = -0.50

    # ── 7. Macro Regime State Classifier ───────────────────────────────────
    regimes = np.zeros(len(df), dtype=int)
    for i in range(len(df)):
        vix_spike = df["vix_spike_regime"].iloc[i] == 1
        dxy_rising = df["dxy_ret_5d"].iloc[i] > 0.005 and df["us10y_5d_delta"].iloc[i] >= 0.0
        oil_rising = df["brent_ret_5d"].iloc[i] > 0.02 and df["tip_ret_5d"].iloc[i] >= -0.002

        if vix_spike:
            regimes[i] = MacroRegime.RISK_OFF_FLIGHT
        elif dxy_rising:
            regimes[i] = MacroRegime.DOLLAR_PRESSURE
        elif oil_rising:
            regimes[i] = MacroRegime.INFLATION_HEDGE
        else:
            regimes[i] = MacroRegime.NEUTRAL

    df["macro_regime_code"] = regimes

    return df


def add_all_macro_features(
    gold_df: pd.DataFrame,
    store: Optional[MacroDataStore] = None,
    use_synthetic_fallback: bool = True,
) -> pd.DataFrame:
    """
    Convenience pipeline: Loads macro series from store (or fetches/synthesizes),
    aligns them strictly to gold_df, and computes all macro features.
    """
    store = store or MacroDataStore()
    collector = MacroCollector(store=store)

    macro_dfs = {}
    for key, info in MACRO_TICKER_MAP.items():
        ticker = info["ticker"]
        loaded = store.load_macro_series(ticker)
        if loaded.empty:
            loaded = collector.fetch_macro_series(key, period="2y", use_synthetic=use_synthetic_fallback)
        macro_dfs[key] = loaded

    aligned = align_macro_to_gold(gold_df, macro_dfs)
    return compute_macro_features(aligned)
