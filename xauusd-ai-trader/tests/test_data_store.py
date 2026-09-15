"""
Tests — Data Store (SQLite)

Tests store/load roundtrip, dataset versioning, and metadata recording.
"""

import sys
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.data_store import DataStore


# ── Helpers ──────────────────────────────────────────────────────────────────

def make_test_df(n: int = 50) -> pd.DataFrame:
    """Create a small test DataFrame."""
    rng = np.random.default_rng(42)
    start = datetime(2025, 1, 6, 0, 0, tzinfo=timezone.utc)
    timestamps = [start + timedelta(hours=i) for i in range(n)]

    base = 2650.0
    close = base + np.cumsum(rng.normal(0, 2, n))
    open_p = close + rng.normal(0, 1, n)
    high = np.maximum(open_p, close) + np.abs(rng.normal(0, 3, n))
    low = np.minimum(open_p, close) - np.abs(rng.normal(0, 3, n))

    return pd.DataFrame({
        "timestamp": pd.DatetimeIndex(timestamps, tz=timezone.utc),
        "open": np.round(open_p, 2),
        "high": np.round(high, 2),
        "low": np.round(low, 2),
        "close": np.round(close, 2),
        "tick_volume": rng.integers(100, 5000, n),
        "spread": rng.integers(20, 50, n),
        "real_volume": np.zeros(n, dtype=int),
    })


@pytest.fixture
def store(tmp_path):
    """Create a temporary DataStore for testing."""
    db_path = tmp_path / "test_research.db"
    return DataStore(db_path)


# ── Tests ────────────────────────────────────────────────────────────────────

class TestStoreAndLoad:
    """Test store/load roundtrip."""

    def test_store_returns_dataset_id(self, store):
        df = make_test_df()
        dataset_id = store.store_raw(df, "XAUUSD", "XAUUSDm", "H1")
        assert dataset_id is not None
        assert len(dataset_id) > 0

    def test_load_returns_same_data(self, store):
        df = make_test_df(20)
        dataset_id = store.store_raw(df, "XAUUSD", "XAUUSDm", "H1")
        loaded = store.load_raw("XAUUSD", "H1", dataset_id=dataset_id)

        assert len(loaded) == len(df)
        # Compare OHLC values
        np.testing.assert_array_almost_equal(loaded["close"].values, df["close"].values, decimal=2)
        np.testing.assert_array_almost_equal(loaded["open"].values, df["open"].values, decimal=2)

    def test_load_empty_for_wrong_symbol(self, store):
        df = make_test_df(10)
        store.store_raw(df, "XAUUSD", "XAUUSDm", "H1")
        loaded = store.load_raw("EURUSD", "H1")
        assert len(loaded) == 0

    def test_load_empty_for_wrong_timeframe(self, store):
        df = make_test_df(10)
        store.store_raw(df, "XAUUSD", "XAUUSDm", "H1")
        loaded = store.load_raw("XAUUSD", "M5")
        assert len(loaded) == 0


class TestDatasetVersioning:
    """Test that datasets are versioned independently."""

    def test_multiple_datasets_get_unique_ids(self, store):
        df1 = make_test_df(10)
        df2 = make_test_df(10)
        id1 = store.store_raw(df1, "XAUUSD", "XAUUSDm", "H1")
        id2 = store.store_raw(df2, "XAUUSD", "XAUUSDm", "H1")
        assert id1 != id2

    def test_list_datasets(self, store):
        df = make_test_df(10)
        store.store_raw(df, "XAUUSD", "XAUUSDm", "H1")
        store.store_raw(df, "XAUUSD", "XAUUSDm", "H4")
        datasets = store.list_datasets()
        assert len(datasets) == 2

    def test_list_datasets_filtered(self, store):
        df = make_test_df(10)
        store.store_raw(df, "XAUUSD", "XAUUSDm", "H1")
        store.store_raw(df, "EURUSD", "EURUSD", "H1")
        xau_datasets = store.list_datasets(symbol="XAUUSD")
        assert len(xau_datasets) == 1

    def test_get_dataset_info(self, store):
        df = make_test_df(10)
        dataset_id = store.store_raw(df, "XAUUSD", "XAUUSDm", "H1", quality_verdict="GOOD")
        info = store.get_dataset_info(dataset_id)
        assert info is not None
        assert info["symbol"] == "XAUUSD"
        assert info["timeframe"] == "H1"
        assert info["row_count"] == 10
        assert info["quality_verdict"] == "GOOD"

    def test_get_latest_dataset_id(self, store):
        df = make_test_df(10)
        id1 = store.store_raw(df, "XAUUSD", "XAUUSDm", "H1")
        id2 = store.store_raw(df, "XAUUSD", "XAUUSDm", "H1")
        latest = store.get_latest_dataset_id("XAUUSD", "H1")
        assert latest == id2  # Most recent


class TestEdgeCases:
    """Test error handling and edge cases."""

    def test_reject_empty_dataframe(self, store):
        df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close"])
        with pytest.raises(ValueError, match="empty"):
            store.store_raw(df, "XAUUSD", "XAUUSDm", "H1")

    def test_reject_missing_columns(self, store):
        df = pd.DataFrame({"timestamp": [1], "close": [100]})
        with pytest.raises(ValueError, match="missing"):
            store.store_raw(df, "XAUUSD", "XAUUSDm", "H1")

    def test_nonexistent_dataset_returns_none(self, store):
        info = store.get_dataset_info("nonexistent-id")
        assert info is None
