"""
Tests — Macro Data Store
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.macro_data_store import MacroDataStore
from data.macro_collector import MacroCollector


@pytest.fixture
def temp_macro_store(tmp_path):
    db_file = tmp_path / "test_macro.db"
    return MacroDataStore(db_path=db_file)


class TestMacroDataStore:
    def test_store_and_load_series(self, temp_macro_store):
        timestamps = pd.date_range("2026-01-01", periods=10, freq="1D", tz=timezone.utc)
        df = pd.DataFrame({
            "timestamp": timestamps,
            "open": np.linspace(100, 110, 10),
            "high": np.linspace(101, 111, 10),
            "low": np.linspace(99, 109, 10),
            "close": np.linspace(100.5, 110.5, 10),
            "volume": np.ones(10) * 1000,
        })

        count = temp_macro_store.store_macro_series("DX-Y.NYB", "US Dollar Index", df)
        assert count == 10

        loaded = temp_macro_store.load_macro_series("DX-Y.NYB")
        assert len(loaded) == 10
        assert "timestamp" in loaded.columns
        assert "close" in loaded.columns
        assert np.isclose(loaded["close"].iloc[0], 100.5)

    def test_date_range_filtering(self, temp_macro_store):
        timestamps = pd.date_range("2026-01-01", periods=20, freq="1D", tz=timezone.utc)
        df = pd.DataFrame({
            "timestamp": timestamps,
            "close": np.linspace(10, 30, 20),
        })
        temp_macro_store.store_macro_series("^VIX", "CBOE VIX", df)

        start = datetime(2026, 1, 5, tzinfo=timezone.utc)
        end = datetime(2026, 1, 10, tzinfo=timezone.utc)
        filtered = temp_macro_store.load_macro_series("^VIX", start=start, end=end)
        assert len(filtered) == 6

    def test_list_tickers(self, temp_macro_store):
        timestamps = pd.date_range("2026-01-01", periods=5, freq="1D", tz=timezone.utc)
        df = pd.DataFrame({"timestamp": timestamps, "close": [1, 2, 3, 4, 5]})
        temp_macro_store.store_macro_series("SI=F", "Silver", df)

        tickers = temp_macro_store.list_available_macro_tickers()
        assert len(tickers) == 1
        assert tickers[0]["ticker"] == "SI=F"
        assert tickers[0]["count"] == 5
