"""
Tests — Macro Feature Engineering
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from features.macro_features import (
    align_macro_to_gold,
    compute_macro_features,
    add_all_macro_features,
    MacroRegime,
    MACRO_FEATURE_COLS,
)
from data.macro_collector import MacroCollector


class TestMacroFeatures:
    def test_align_macro_to_gold(self):
        gold_ts = pd.date_range("2026-01-01 00:00:00", periods=48, freq="1h", tz=timezone.utc)
        gold_df = pd.DataFrame({
            "timestamp": gold_ts,
            "open": np.ones(48) * 2650.0,
            "high": np.ones(48) * 2660.0,
            "low": np.ones(48) * 2640.0,
            "close": np.ones(48) * 2655.0,
        })

        macro_ts = pd.date_range("2026-01-01", periods=2, freq="1D", tz=timezone.utc)
        dxy_df = pd.DataFrame({"timestamp": macro_ts, "close": [103.0, 104.0]})
        vix_df = pd.DataFrame({"timestamp": macro_ts, "close": [15.0, 18.0]})

        aligned = align_macro_to_gold(gold_df, {"DXY": dxy_df, "VIX": vix_df})
        assert "dxy_close" in aligned.columns
        assert "vix_close" in aligned.columns
        assert len(aligned) == 48

        # Bars on Day 1 should have Day 1 macro close (103.0)
        assert aligned["dxy_close"].iloc[0] == 103.0
        assert aligned["dxy_close"].iloc[23] == 103.0
        # Bars on Day 2 should have Day 2 macro close (104.0)
        assert aligned["dxy_close"].iloc[24] == 104.0

    def test_compute_macro_features(self):
        ts = pd.date_range("2026-01-01", periods=150, freq="1h", tz=timezone.utc)
        aligned_df = pd.DataFrame({
            "timestamp": ts,
            "close": np.linspace(2600, 2700, 150),
            "dxy_close": np.linspace(102, 104, 150),
            "us10y_close": np.linspace(4.1, 4.3, 150),
            "us02y_close": np.linspace(4.4, 4.5, 150),
            "tip_close": np.linspace(105, 106, 150),
            "vix_close": np.ones(150) * 16.0,
            "xag_close": np.linspace(30, 32, 150),
            "brent_close": np.linspace(80, 85, 150),
        })

        res = compute_macro_features(aligned_df)
        for col in MACRO_FEATURE_COLS:
            assert col in res.columns, f"Missing expected macro feature: {col}"

        # Yield curve slope = 10Y - 2Y
        expected_slope = res["us10y_yield"] - res["us02y_yield"]
        assert np.allclose(res["yield_curve_slope"], expected_slope)

        # Gold/Silver ratio = Gold / XAG
        expected_gsr = res["close"] / res["xag_close"]
        assert np.allclose(res["gold_silver_ratio"], expected_gsr)

    def test_regime_classification(self):
        ts = pd.date_range("2026-01-01", periods=150, freq="1h", tz=timezone.utc)
        df = pd.DataFrame({
            "timestamp": ts,
            "close": np.ones(150) * 2650.0,
            "dxy_close": np.linspace(100, 105, 150),  # Surging DXY
            "us10y_close": np.linspace(4.0, 4.5, 150), # Surging Yield
            "us02y_close": np.ones(150) * 4.2,
            "tip_close": np.ones(150) * 105.0,
            "vix_close": np.ones(150) * 14.0,
            "xag_close": np.ones(150) * 31.0,
            "brent_close": np.ones(150) * 80.0,
        })
        res = compute_macro_features(df)
        # End of series should reflect DOLLAR_PRESSURE
        assert res["macro_regime_code"].iloc[-1] == MacroRegime.DOLLAR_PRESSURE
