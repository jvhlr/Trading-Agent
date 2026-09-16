"""
Tests — Macro Look-Ahead Leakage Prevention (Hard System Invariant)
"""

import sys
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from features.macro_features import align_macro_to_gold, compute_macro_features


class TestMacroLookAhead:
    """
    Verifies that mutating macro values at future timestamp T_future
    has ZERO impact on features computed at earlier timestamp T_past.
    """

    def test_no_future_macro_leakage(self):
        gold_ts = pd.date_range("2026-01-01", periods=100, freq="1h", tz=timezone.utc)
        gold_df = pd.DataFrame({
            "timestamp": gold_ts,
            "open": np.linspace(2600, 2700, 100),
            "high": np.linspace(2605, 2705, 100),
            "low": np.linspace(2595, 2695, 100),
            "close": np.linspace(2602, 2702, 100),
        })

        macro_ts = pd.date_range("2026-01-01", periods=5, freq="1D", tz=timezone.utc)
        dxy_base = pd.DataFrame({
            "timestamp": macro_ts,
            "close": [102.0, 102.5, 103.0, 103.5, 104.0],
        })

        # Aligned features run 1
        aligned1 = align_macro_to_gold(gold_df, {"DXY": dxy_base})
        feat1 = compute_macro_features(aligned1)

        # Mutate future Day 5 DXY value to an extreme number (e.g. 500.0)
        dxy_mutated = dxy_base.copy()
        dxy_mutated.loc[4, "close"] = 500.0

        aligned2 = align_macro_to_gold(gold_df, {"DXY": dxy_mutated})
        feat2 = compute_macro_features(aligned2)

        # Features before Day 5 (index 0 to 95) MUST be strictly identical
        past_idx = 90
        for col in ["dxy_close", "dxy_ret_1d", "dxy_ret_5d", "dxy_sma20_dist"]:
            val1 = feat1[col].iloc[:past_idx].values
            val2 = feat2[col].iloc[:past_idx].values
            assert np.allclose(val1, val2), f"Lookahead leakage detected in column {col}!"
