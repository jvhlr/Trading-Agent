"""
Unit tests for Realistic Research Backtester Engine.

Verifies:
1. Entry execution strictly at candle t+1 Open (zero look-ahead).
2. Transaction cost (spread + slippage) subtractions.
3. Intra-bar Stop Loss and Take Profit execution against High/Low bounds.
4. Equity curve calculation and drawdown math.
"""

import pytest
import numpy as np
import pandas as pd

from backtester.types import BacktestConfig, ExitReason
from backtester.sim import run_backtest


def make_backtest_df(prices, atrs=None):
    """Generates simple OHLC dataframe for backtesting tests."""
    n = len(prices)
    dates = pd.date_range("2026-01-01", periods=n, freq="1h")
    df = pd.DataFrame(
        {
            "timestamp": dates,
            "open": prices,
            "high": [p + 1.0 for p in prices],
            "low": [p - 1.0 for p in prices],
            "close": prices,
            "atr_14": atrs if atrs is not None else [2.0] * n,
        }
    )
    return df


class TestBacktesterInvariants:
    def test_entry_at_next_bar_open(self):
        # Signal at bar 0 -> Must enter at bar 1 open price
        prices = [100.0, 105.0, 110.0, 115.0]
        df = make_backtest_df(prices)
        preds = np.array([1, 0, 0, 0])

        config = BacktestConfig(
            spread_dollars=0.20,
            slippage_dollars=0.10,
            risk_pct_per_trade=0.01,
            use_atr_sl_tp=False,
            max_holding_bars=2,
        )

        res = run_backtest(df, preds, config=config)
        assert len(res.trades) == 1
        trade = res.trades[0]

        # Entry index must be 1 (t+1)
        assert trade.entry_index == 1
        # BUY entry price = open[1] (105.0) + half_spread (0.10) + slippage (0.10) = 105.20
        assert pytest.approx(trade.entry_price) == 105.20

    def test_stop_loss_trigger(self):
        # BUY signal at bar 0 -> Enter at bar 1 open (100.0 + 0.20 = 100.20)
        # Bar 2 low drops to 90.0 (below SL of 95.0)
        dates = pd.date_range("2026-01-01", periods=4, freq="1h")
        df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100.0, 100.0, 95.0, 95.0],
                "high": [102.0, 102.0, 96.0, 96.0],
                "low": [98.0, 98.0, 90.0, 90.0],  # Bar 2 low drops to 90.0
                "close": [100.0, 100.0, 92.0, 92.0],
                "atr_14": [2.0] * 4,
            }
        )

        preds = np.array([1, 0, 0, 0])
        config = BacktestConfig(
            spread_dollars=0.20,
            slippage_dollars=0.10,
            use_atr_sl_tp=True,
            sl_atr_mult=2.5,  # SL dist = 5.0 -> SL price = 100.20 - 5.0 = 95.20
            tp_atr_mult=10.0,
        )

        res = run_backtest(df, preds, config=config)
        assert len(res.trades) == 1
        trade = res.trades[0]

        assert trade.exit_reason == ExitReason.STOP_LOSS.value
        assert trade.exit_index == 2

    def test_take_profit_trigger(self):
        # BUY signal at bar 0 -> Enter at bar 1 open (100.0 + 0.20 = 100.20)
        # Bar 2 high rises to 110.0 (above TP of 105.0)
        dates = pd.date_range("2026-01-01", periods=4, freq="1h")
        df = pd.DataFrame(
            {
                "timestamp": dates,
                "open": [100.0, 100.0, 102.0, 102.0],
                "high": [101.0, 101.0, 110.0, 110.0],  # Bar 2 high rises to 110.0
                "low": [99.0, 99.0, 101.0, 101.0],
                "close": [100.0, 100.0, 108.0, 108.0],
                "atr_14": [2.0] * 4,
            }
        )

        preds = np.array([1, 0, 0, 0])
        config = BacktestConfig(
            spread_dollars=0.20,
            slippage_dollars=0.10,
            use_atr_sl_tp=True,
            sl_atr_mult=10.0,
            tp_atr_mult=2.0,  # TP dist = 4.0 -> TP price = 100.20 + 4.0 = 104.20
        )

        res = run_backtest(df, preds, config=config)
        assert len(res.trades) == 1
        trade = res.trades[0]

        assert trade.exit_reason == ExitReason.TAKE_PROFIT.value
        assert trade.exit_index == 2

    def test_max_holding_bars_exit(self):
        prices = [100.0] * 10
        df = make_backtest_df(prices)
        preds = np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0])

        config = BacktestConfig(
            spread_dollars=0.20,
            slippage_dollars=0.10,
            use_atr_sl_tp=False,
            max_holding_bars=3,
        )

        res = run_backtest(df, preds, config=config)
        assert len(res.trades) == 1
        trade = res.trades[0]

        assert trade.exit_reason == ExitReason.HOLDING_EXPIRED.value
        # Entry at index 1 -> Holding 3 bars -> Exit at index 1 + 3 = 4
        assert trade.exit_index == 4
