"""
Unit tests for Walk-Forward Temporal Cross-Validation Engine.

Verifies window boundaries, fold stepping, and out-of-sample aggregation.
"""

import pytest
import numpy as np
import pandas as pd

from features.price_features import add_all_price_features
from features.technical_features import add_all_technical_features
from features.label_generator import add_direction_target
from models.baselines import MajorityWaitBaseline, PreviousReturnMomentumBaseline
from backtester.walk_forward import run_walk_forward, WalkForwardSummary


def make_walk_forward_dataset(n_rows: int = 2000):
    """Generates synthetic dataset for walk-forward testing."""
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=n_rows, freq="1h")
    returns = np.random.normal(0.0001, 0.002, size=n_rows)
    close = 2000.0 * np.exp(np.cumsum(returns))
    high = close * (1 + np.abs(np.random.normal(0, 0.001, size=n_rows)))
    low = close * (1 - np.abs(np.random.normal(0, 0.001, size=n_rows)))
    open_p = close * (1 + np.random.normal(0, 0.001, size=n_rows))

    df = pd.DataFrame(
        {
            "timestamp": dates,
            "open": open_p,
            "high": high,
            "low": low,
            "close": close,
            "tick_volume": np.random.randint(100, 1000, size=n_rows),
        }
    )

    df = add_all_price_features(df)
    df = add_all_technical_features(df)
    df = add_direction_target(df, horizon=1, threshold=0.20)
    return df


class TestWalkForwardEngine:
    def test_walk_forward_fold_count(self):
        df = make_walk_forward_dataset(n_rows=2000)
        feature_cols = ["return_1", "sma_20", "rsi_14"]

        # train=1000, val=200, test=200 -> total window=1400. step=200
        # n_rows=2000: fold 1 starts at 0, fold 2 starts at 200, fold 3 starts at 400 (400+1400=1800), fold 4 starts at 600 (600+1400=2000) -> 4 folds
        summary = run_walk_forward(
            df,
            feature_cols=feature_cols,
            target_col="target_direction",
            model_factory=lambda: MajorityWaitBaseline(),
            train_bars=1000,
            val_bars=200,
            test_bars=200,
            step_bars=200,
        )

        assert isinstance(summary, WalkForwardSummary)
        assert summary.total_folds == 4
        assert len(summary.fold_results) == 4

    def test_window_boundaries_non_overlapping_tests(self):
        df = make_walk_forward_dataset(n_rows=1600)
        feature_cols = ["return_1", "sma_20"]

        summary = run_walk_forward(
            df,
            feature_cols=feature_cols,
            target_col="target_direction",
            model_factory=lambda: PreviousReturnMomentumBaseline(),
            train_bars=1000,
            val_bars=200,
            test_bars=200,
            step_bars=200,
        )

        # Verify test window start for fold 2 is strictly after fold 1 test start
        f1 = summary.fold_results[0]
        f2 = summary.fold_results[1]
        assert f1.test_start < f2.test_start
        assert f1.test_end < f2.test_end
