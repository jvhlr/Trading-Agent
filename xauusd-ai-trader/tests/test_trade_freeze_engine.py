# coding: utf-8
# Tests -- TradeFreezeEngine (Phase 5)
#
# TRAP: two paths -- primary (get_signals) and fallback (predict only).
# Fresh engine per test to prevent calendar cache leak between cases.
#
# NOTE on calendar loading: TradeFreezeEngine lazily fetches calendar events
# covering [df.timestamp.min(), df.timestamp.max()].  To trigger the freeze
# for a bar BEFORE an event, the DataFrame must span at least up to the event
# time so the event appears in the loaded calendar window.  Tests below pass a
# range of bars that brackets the event.
import sys, numpy as np, pandas as pd, pytest
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.baselines import BaseModel
from models.trade_freeze_engine import TradeFreezeEngine
from models.macro_gated_model import MacroGatedModel
from models.classifiers import GradientBoostingModel

NFP_JAN2025 = datetime(2025, 1, 3, 13, 30, tzinfo=timezone.utc)


def _utc(*args): return datetime(*args, tzinfo=timezone.utc)


def _make_ohlc_df(timestamps, base_price=1950.0):
    rows = []
    p = base_price
    for ts in timestamps:
        p += np.random.normal(0, 0.5)
        rows.append({'timestamp': ts, 'open': p, 'high': p+1.0,
                     'low': p-1.0, 'close': p, 'volume': 100.0})
    return pd.DataFrame(rows)


def _span(target_ts, extra_minutes=60):
    ''' Return [target_ts, target_ts + extra_minutes] so the event is in window.'''
    return [target_ts, target_ts + timedelta(minutes=extra_minutes)]


class MockSignalModel(BaseModel):
    def __init__(self, signals):
        super().__init__(name='MockSignal')
        self._signals = signals
    def fit(self, X, y): self.is_fitted = True; return self
    def predict(self, X): return np.array([0]*len(X))
    def predict_proba(self, X): return np.zeros((len(X), 3))
    def get_signals(self, df):
        return pd.Series(self._signals[:len(df)], index=df.index)


class MockPredictOnlyModel(BaseModel):
    def __init__(self): super().__init__(name='MockPredictOnly')
    def fit(self, X, y): self.is_fitted = True; return self
    def predict(self, X): return np.array(['BUY']*len(X), dtype=object)
    def predict_proba(self, X): return np.zeros((len(X), 3))


# PRIMARY PATH (base model has get_signals)

class TestTradeFreezeEnginePrimaryPath:
    # NFP on 2025-01-03 13:30 UTC (first Friday of Jan 2025).

    def _engine(self, timestamps, signals, freeze_minutes=30):
        base = MockSignalModel(signals)
        engine = TradeFreezeEngine(base, freeze_minutes=freeze_minutes)
        df = _make_ohlc_df(timestamps)
        return engine, df

    def test_bar_30min_before_nfp_buy_becomes_wait(self):
        # Bar at NFP-30min; span to NFP+60 so the event loads.
        ts = NFP_JAN2025 - timedelta(minutes=30)
        timestamps = _span(ts, extra_minutes=90)
        engine, df = self._engine(timestamps, ['BUY', 'WAIT'])
        assert engine.get_signals(df).iloc[0] == 'WAIT'

    def test_bar_at_13_00_is_frozen(self):
        ts = _utc(2025, 1, 3, 13, 0)
        timestamps = _span(ts, extra_minutes=90)
        engine, df = self._engine(timestamps, ['BUY', 'WAIT'])
        assert engine.get_signals(df).iloc[0] == 'WAIT'

    def test_bar_at_12_59_stays_buy(self):
        # 31 min before NFP -- just outside 30-min window.
        ts = _utc(2025, 1, 3, 12, 59)
        timestamps = _span(ts, extra_minutes=120)
        engine, df = self._engine(timestamps, ['BUY', 'WAIT'])
        assert engine.get_signals(df).iloc[0] == 'BUY'

    def test_bar_at_14_01_stays_buy(self):
        # 31 min after NFP -- just outside 30-min window.
        ts = _utc(2025, 1, 3, 14, 1)
        timestamps = _span(ts, extra_minutes=30)
        engine, df = self._engine(timestamps, ['BUY', 'WAIT'])
        assert engine.get_signals(df).iloc[0] == 'BUY'

    def test_wait_stays_wait(self):
        ts = NFP_JAN2025 - timedelta(minutes=10)
        timestamps = _span(ts, extra_minutes=60)
        engine, df = self._engine(timestamps, ['WAIT', 'WAIT'])
        assert engine.get_signals(df).iloc[0] == 'WAIT'

    def test_sell_near_event_becomes_wait(self):
        # Bar at NFP+15min; span from NFP-60 so the event loads.
        ts = NFP_JAN2025 + timedelta(minutes=15)
        timestamps = [NFP_JAN2025 - timedelta(minutes=60), ts]
        engine, df = self._engine(timestamps, ['WAIT', 'SELL'])
        assert engine.get_signals(df).iloc[1] == 'WAIT'

    def test_custom_freeze_5min_bar_at_13_40_stays_buy(self):
        # 10 min after NFP -- outside 5-min window.
        ts = _utc(2025, 1, 3, 13, 40)
        timestamps = _span(ts, extra_minutes=30)
        engine, df = self._engine(timestamps, ['BUY', 'WAIT'], freeze_minutes=5)
        assert engine.get_signals(df).iloc[0] == 'BUY'

    def test_custom_freeze_5min_bar_at_13_34_frozen(self):
        # Bar at NFP+4min; span from NFP-60 so the event loads.
        ts = _utc(2025, 1, 3, 13, 34)
        timestamps = [NFP_JAN2025 - timedelta(minutes=60), ts]
        engine, df = self._engine(timestamps, ['WAIT', 'BUY'], freeze_minutes=5)
        assert engine.get_signals(df).iloc[1] == 'WAIT'

    def test_no_events_in_range_signals_unchanged(self):
        # Mid-Jan week: no NFP (day>7), no FOMC (Jan=odd), so calendar empty.
        timestamps = [_utc(2025,1,14,10), _utc(2025,1,15,10), _utc(2025,1,16,10)]
        signals = ['BUY', 'SELL', 'BUY']
        engine, df = self._engine(timestamps, signals)
        assert list(engine.get_signals(df)) == signals


# FALLBACK PATH (base model has only predict, no get_signals)

class TestTradeFreezeEngineFallbackPath:
    def _make_long_ohlc(self, freeze_ts):
        n = 300
        np.random.seed(42)
        start = freeze_ts - timedelta(hours=n - 1)
        timestamps = [start + timedelta(hours=i) for i in range(n)]
        return _make_ohlc_df(timestamps)

    def test_buy_inside_freeze_window_becomes_wait(self):
        df = self._make_long_ohlc(NFP_JAN2025)
        base = MockPredictOnlyModel()
        engine = TradeFreezeEngine(base, freeze_minutes=30)
        result = engine.get_signals(df)
        assert result.iloc[-1] == 'WAIT', f'Expected WAIT, got {result.iloc[-1]}'


# PLUMBING

class TestTradeFreezeEnginePlumbing:
    def test_name_includes_base_name(self):
        engine = TradeFreezeEngine(MockSignalModel(['BUY']))
        assert 'MockSignal' in engine.name and 'Freeze-Protected' in engine.name

    def test_fit_passes_through(self):
        base = MockSignalModel(['BUY'])
        TradeFreezeEngine(base).fit(np.array([[1.0]]), np.array([1]))
        assert base.is_fitted is True

    def test_predict_passes_through(self):
        base = MockSignalModel(['BUY'])
        result = TradeFreezeEngine(base).predict(np.array([[1.0]]))
        assert list(result) == [0]

    def test_empty_df_returns_empty_series(self):
        base = MockSignalModel([])
        engine = TradeFreezeEngine(base)
        df = pd.DataFrame(columns=['timestamp','open','high','low','close','volume'])
        result = engine.get_signals(df)
        assert isinstance(result, pd.Series) and len(result) == 0

    def test_calendar_cache_starts_empty(self):
        engine = TradeFreezeEngine(MockSignalModel(['BUY']))
        assert engine.calendar_df.empty


# INTEGRATION: exact backtest.py wiring

class TestTradeFreezeEngineIntegration:
    def test_production_wiring(self):
        np.random.seed(0)
        start = _utc(2025, 1, 14, 0, 0)
        timestamps = [start + timedelta(hours=i) for i in range(50)]
        df = _make_ohlc_df(timestamps)
        gb = GradientBoostingModel(n_estimators=10, learning_rate=0.1,
                                   max_depth=2, random_state=42)
        macro_gated = MacroGatedModel(gb)
        engine = TradeFreezeEngine(macro_gated, freeze_minutes=30)
        result = engine.get_signals(df)
        assert isinstance(result, pd.Series)
        assert len(result) == len(df)
        assert all(s in ('BUY', 'SELL', 'WAIT') for s in result)
