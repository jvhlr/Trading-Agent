# XAUUSD AI Trading Research System — Backtester Package

from .backtest_types import Trade, BacktestConfig, BacktestResult, ExitReason
from .sim import run_backtest
from .walk_forward import run_walk_forward, WalkForwardSummary, WalkForwardFoldResult

__all__ = [
    "Trade",
    "BacktestConfig",
    "BacktestResult",
    "ExitReason",
    "run_backtest",
    "run_walk_forward",
    "WalkForwardSummary",
    "WalkForwardFoldResult",
]
