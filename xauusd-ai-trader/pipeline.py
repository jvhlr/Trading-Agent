"""
XAUUSD AI Trading Research System — Shared Data & Feature Pipeline

Centralizes the repeated data-loading, validation, and feature-engineering
steps that were previously duplicated across train.py and backtest.py.

All callers receive a clean, fully-featured DataFrame plus the list of usable
ML feature column names — ready for model training or backtesting.

Usage:
    from pipeline import load_and_prepare_data, EXCLUDE_COLS

    df, feature_cols = load_and_prepare_data(
        synthetic=True,
        days=180,
        timeframe="H1",
        symbol="XAUUSD",
        include_macro=True,
        direction_threshold=0.30,
    )
"""

import sys
import logging
from pathlib import Path
from typing import Optional

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.data_collector import generate_sample_data
from data.data_validator import validate, Verdict
from features.price_features import add_all_price_features
from features.technical_features import add_all_technical_features
from features.structure_features import add_all_structure_features
from features.label_generator import add_direction_target

logger = logging.getLogger(__name__)

# Columns that are raw price/meta data and must never be used as ML features.
EXCLUDE_COLS: frozenset[str] = frozenset({
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "tick_volume",
    "real_volume",
    "spread",
    "target_direction",
    "target_return",
    "target_binary",
    "structure_trend",
    "swing_high",
    "swing_low",
    "swing_high_price",
    "swing_low_price",
    "prev_swing_high",
    "prev_swing_low",
    "swing_pattern_high",
    "swing_pattern_low",
})

# Number of leading rows to ignore when checking NaN presence (feature warmup).
_WARMUP_ROWS = 200


def _load_raw_data(
    synthetic: bool,
    days: int,
    timeframe: str,
    symbol: str,
) -> Optional[pd.DataFrame]:
    """
    Load raw OHLCV data — either from the SQLite store (real) or the
    synthetic generator (development fallback).

    Returns the DataFrame on success, or None if no data could be obtained.
    """
    if synthetic:
        df, _ = generate_sample_data(
            timeframe=timeframe, days=days, internal_symbol=symbol
        )
        return df

    # Attempt to load stored real data; fall back to synthetic on any failure.
    try:
        from data.data_store import DataStore

        store = DataStore()
        df = store.load_raw(symbol=symbol, timeframe=timeframe)
        if not df.empty:
            return df

        logger.warning(
            "Data store is empty for %s %s — falling back to synthetic data.",
            symbol, timeframe,
        )
    except Exception as exc:
        logger.warning(
            "Could not load stored data (%s) — falling back to synthetic data.", exc
        )

    df, _ = generate_sample_data(
        timeframe=timeframe, days=days, internal_symbol=symbol
    )
    return df


def _select_feature_cols(df: pd.DataFrame) -> list[str]:
    """
    Return only numeric, fully-populated (post-warmup) non-excluded columns.

    A column qualifies when:
      - It is not in EXCLUDE_COLS.
      - pandas considers it numeric.
      - It has zero NaN values after the first _WARMUP_ROWS rows.
    """
    return [
        col
        for col in df.columns
        if col not in EXCLUDE_COLS
        and pd.api.types.is_numeric_dtype(df[col])
        and df[col].iloc[_WARMUP_ROWS:].isna().sum() == 0
    ]


def load_and_prepare_data(
    synthetic: bool = True,
    days: int = 180,
    timeframe: str = "H1",
    symbol: str = "XAUUSD",
    include_macro: bool = False,
    direction_threshold: float = 0.30,
) -> tuple[pd.DataFrame, list[str]]:
    """
    End-to-end data & feature pipeline shared by train.py and backtest.py.

    Steps:
        1. Load raw OHLCV data (real store or synthetic fallback).
        2. Validate data quality — raises SystemExit on FAIL verdict.
        3. Engineer price, technical, structure, and (optionally) macro features.
        4. Generate the 3-class directional target label.
        5. Select the ML-ready feature column list.

    Args:
        synthetic:           Use synthetic data generator instead of data store.
        days:                Days of historical data (used by synthetic generator).
        timeframe:           Candle timeframe string, e.g. "H1".
        symbol:              Internal symbol name, e.g. "XAUUSD".
        include_macro:       Whether to add cross-market macro features.
        direction_threshold: Dollar threshold for BUY/SELL vs WAIT labelling.

    Returns:
        (df, feature_cols) — the fully-featured DataFrame and a list of
        ML-ready column names.

    Raises:
        SystemExit: If data quality validation fails.
    """
    # ── 1. Load ──────────────────────────────────────────────────────────────
    df = _load_raw_data(synthetic=synthetic, days=days, timeframe=timeframe, symbol=symbol)

    if df is None or df.empty:
        logger.error("No data available after load attempt.")
        print("[ERROR] No data available. Use synthetic or configure real data source.")
        sys.exit(1)

    # ── 2. Validate ───────────────────────────────────────────────────────────
    report = validate(df, timeframe=timeframe)
    print(
        f"\n[DATA QUALITY] Verdict: {report.verdict.name} | Bars: {report.row_count}"
    )

    if report.verdict == Verdict.FAIL:
        logger.error("Data validation FAILED — cannot proceed.")
        print("[FAIL] Data quality validation failed. Fix issues before continuing.")
        sys.exit(1)

    # ── 3. Feature Engineering ────────────────────────────────────────────────
    print("[FEATURES] Engineering price, technical, and market structure features...")
    df = add_all_price_features(df)
    df = add_all_technical_features(df)
    df = add_all_structure_features(df)

    if include_macro:
        from features.macro_features import add_all_macro_features
        print("[FEATURES] Aligning macro & intermarket features (zero look-ahead)...")
        df = add_all_macro_features(df, use_synthetic_fallback=True)

    # ── 4. Labels ─────────────────────────────────────────────────────────────
    df = add_direction_target(
        df,
        horizon=1,
        threshold=direction_threshold,
        target_col="target_direction",
    )

    # ── 5. Feature Selection ──────────────────────────────────────────────────
    feature_cols = _select_feature_cols(df)
    print(f"[FEATURES] {len(feature_cols)} ML-ready feature columns selected.")

    return df, feature_cols
