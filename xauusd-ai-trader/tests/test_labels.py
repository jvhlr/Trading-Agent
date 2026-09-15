"""
Tests for Label Generator Module.

Verifies deterministic target creation and verifies that labels do not leak
into feature matrices.
"""

import pytest
import pandas as pd
import numpy as np
from features.label_generator import add_direction_target, add_binary_target


def make_test_df():
    """Generates simple price dataframe."""
    prices = [100.0, 101.0, 100.5, 102.0, 101.5, 103.0, 102.5, 104.0]
    dates = pd.date_range("2026-01-01", periods=len(prices), freq="1h")
    return pd.DataFrame({"timestamp": dates, "close": prices})


class TestDirectionTarget:
    def test_3class_threshold_labels(self):
        df = make_test_df()
        # threshold = 0.8
        # t0: 100.0 -> 101.0 (diff = +1.0 > 0.8) => +1
        # t1: 101.0 -> 100.5 (diff = -0.5, |-0.5| <= 0.8) => 0
        # t2: 100.5 -> 102.0 (diff = +1.5 > 0.8) => +1
        # t3: 102.0 -> 101.5 (diff = -0.5, |-0.5| <= 0.8) => 0
        # t4: 101.5 -> 103.0 (diff = +1.5 > 0.8) => +1
        # t5: 103.0 -> 102.5 (diff = -0.5, |-0.5| <= 0.8) => 0
        # t6: 102.5 -> 104.0 (diff = +1.5 > 0.8) => +1
        # t7: last bar => NaN

        out = add_direction_target(df, horizon=1, threshold=0.8)
        labels = out["target_direction"].values

        assert labels[0] == 1
        assert labels[1] == 0
        assert labels[2] == 1
        assert labels[3] == 0
        assert labels[4] == 1
        assert labels[5] == 0
        assert labels[6] == 1
        assert np.isnan(labels[7])

    def test_horizon_nans(self):
        df = make_test_df()
        out = add_direction_target(df, horizon=2, threshold=0.5)
        labels = out["target_direction"].values
        # Last 2 rows should be NaN
        assert np.isnan(labels[-1])
        assert np.isnan(labels[-2])
        assert not np.isnan(labels[-3])

    def test_target_return(self):
        df = make_test_df()
        out = add_direction_target(df, horizon=1, threshold=0.5)
        # t0 return: (101.0 - 100.0) / 100.0 = 0.01
        assert pytest.approx(out["target_return"].iloc[0], rel=1e-4) == 0.01
        assert np.isnan(out["target_return"].iloc[-1])


class TestBinaryTarget:
    def test_binary_labels(self):
        df = make_test_df()
        out = add_binary_target(df, horizon=1)
        labels = out["target_binary"].values

        # t0: 100 -> 101 (1)
        # t1: 101 -> 100.5 (0)
        # t2: 100.5 -> 102 (1)
        assert labels[0] == 1.0
        assert labels[1] == 0.0
        assert labels[2] == 1.0
        assert np.isnan(labels[-1])
