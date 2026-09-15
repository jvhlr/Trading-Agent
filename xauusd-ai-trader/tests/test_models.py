"""
Tests for Models, Dataset Builder, Baselines, Classifiers, and Evaluation Modules.
"""

import pytest
import numpy as np
import pandas as pd

from features.price_features import add_all_price_features
from features.technical_features import add_all_technical_features
from features.structure_features import add_all_structure_features
from features.label_generator import add_direction_target

from models.dataset_builder import build_dataset, DatasetSplit
from models.baselines import (
    RandomBaseline,
    MajorityWaitBaseline,
    PreviousReturnMomentumBaseline,
    SMACrossoverBaseline,
)
from models.classifiers import (
    LogisticRegressionModel,
    RandomForestModel,
    GradientBoostingModel,
)
from models.evaluation import (
    evaluate_classification,
    evaluate_financial,
)


def make_sample_dataset(n_rows: int = 300):
    """Creates synthetic OHLCV dataframe with features and target for testing."""
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


class TestDatasetBuilder:
    def test_chronological_splits(self):
        df = make_sample_dataset(n_rows=300)
        feature_cols = ["return_1", "sma_20", "rsi_14"]
        ds = build_dataset(
            df,
            feature_cols=feature_cols,
            target_col="target_direction",
            train_ratio=0.6,
            val_ratio=0.2,
            test_ratio=0.2,
        )

        n_total = len(ds.raw_df_cleaned)
        assert len(ds.X_train) == int(n_total * 0.6)
        assert len(ds.X_val) == int(n_total * 0.2)
        assert len(ds.X_test) == n_total - len(ds.X_train) - len(ds.X_val)

        # Check timestamp ordering between splits
        assert ds.timestamps_train.iloc[-1] < ds.timestamps_val.iloc[0]
        assert ds.timestamps_val.iloc[-1] < ds.timestamps_test.iloc[0]

    def test_scaler_no_leakage(self):
        df = make_sample_dataset(n_rows=200)
        feature_cols = ["return_1", "sma_20"]
        ds = build_dataset(df, feature_cols=feature_cols, scale=True)

        # Scaler mean should match train mean
        train_raw = ds.raw_df_cleaned[feature_cols].iloc[: len(ds.X_train)].values
        mean_expected = np.mean(train_raw, axis=0)
        assert np.allclose(ds.scaler.mean_, mean_expected)


class TestBaselines:
    def test_majority_wait_baseline(self):
        model = MajorityWaitBaseline()
        X = np.random.randn(50, 4)
        y = np.random.choice([-1, 0, 1], size=50)

        model.fit(X, y)
        preds = model.predict(X)
        probs = model.predict_proba(X)

        assert np.all(preds == 0)
        assert probs.shape == (50, 3)
        assert np.all(probs[:, 1] == 1.0)

    def test_random_baseline(self):
        model = RandomBaseline(weighted=True, seed=42)
        X = np.random.randn(100, 4)
        y = np.array([1] * 70 + [-1] * 20 + [0] * 10)

        model.fit(X, y)
        preds = model.predict(X)
        probs = model.predict_proba(X)

        assert len(preds) == 100
        assert probs.shape == (100, 3)
        assert pytest.approx(probs[0, 2], rel=1e-2) == 0.7  # Class 1 is 70%

    def test_momentum_baseline(self):
        model = PreviousReturnMomentumBaseline(return_feature_idx=0)
        X = np.array([[0.05, 10.0], [-0.02, 5.0], [0.0, 3.0]])

        preds = model.predict(X)
        assert preds[0] == 1
        assert preds[1] == -1
        assert preds[2] == 0


class TestClassifiers:
    def test_logistic_regression(self):
        model = LogisticRegressionModel()
        X = np.random.randn(100, 5)
        y = np.random.choice([-1, 0, 1], size=100)

        model.fit(X, y)
        preds = model.predict(X)
        probs = model.predict_proba(X)

        assert len(preds) == 100
        assert probs.shape == (100, 3)
        assert np.allclose(probs.sum(axis=1), 1.0)

    def test_random_forest(self):
        model = RandomForestModel(n_estimators=10, max_depth=3)
        X = np.random.randn(100, 5)
        y = np.random.choice([-1, 0, 1], size=100)

        model.fit(X, y)
        preds = model.predict(X)
        probs = model.predict_proba(X)

        assert len(preds) == 100
        assert probs.shape == (100, 3)

    def test_gradient_boosting(self):
        model = GradientBoostingModel(n_estimators=10, max_depth=2)
        X = np.random.randn(100, 5)
        y = np.random.choice([-1, 0, 1], size=100)

        model.fit(X, y)
        preds = model.predict(X)
        probs = model.predict_proba(X)

        assert len(preds) == 100
        assert probs.shape == (100, 3)


class TestEvaluation:
    def test_classification_metrics(self):
        y_true = np.array([-1, 0, 1, 1, -1, 0])
        y_pred = np.array([-1, 0, 1, 0, -1, 1])
        y_prob = np.array(
            [
                [0.8, 0.1, 0.1],
                [0.1, 0.8, 0.1],
                [0.1, 0.1, 0.8],
                [0.2, 0.6, 0.2],
                [0.7, 0.2, 0.1],
                [0.1, 0.3, 0.6],
            ]
        )

        metrics = evaluate_classification(y_true, y_pred, y_prob)
        assert 0.0 <= metrics.accuracy <= 1.0
        assert 0.0 <= metrics.f1_macro <= 1.0
        assert metrics.brier_score >= 0.0

    def test_financial_metrics(self):
        y_true = np.array([1, -1, 1, -1])
        y_pred = np.array([1, -1, 1, 1])  # 3 trades
        returns = np.array([0.01, -0.01, 0.005, -0.005])

        metrics = evaluate_financial(y_true, y_pred, returns, spread_pct=0.00015)
        assert metrics.n_trades == 4
        assert metrics.win_rate > 0.0
