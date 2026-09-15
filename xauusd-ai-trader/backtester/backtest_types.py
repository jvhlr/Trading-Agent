"""
Types and Configuration Dataclasses for XAUUSD Research Backtester.

Renamed to backtest_types.py to prevent shadowing Python's standard library 'types' module.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import pandas as pd
import numpy as np


class ExitReason(str, Enum):
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    HOLDING_EXPIRED = "HOLDING_EXPIRED"
    SIGNAL_REVERSAL = "SIGNAL_REVERSAL"
    END_OF_DATA = "END_OF_DATA"


@dataclass
class Trade:
    """Dataclass representing an executed trade."""

    trade_id: int
    side: int  # +1 for BUY, -1 for SELL
    entry_index: int
    entry_time: pd.Timestamp
    entry_price: float
    units: float

    exit_index: Optional[int] = None
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None

    sl_price: Optional[float] = None
    tp_price: Optional[float] = None

    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    return_pct: float = 0.0
    exit_reason: Optional[str] = None


@dataclass
class BacktestConfig:
    """Configuration settings for realistic backtest execution simulation."""

    initial_capital: float = 10_000.0
    spread_dollars: float = 0.30  # XAUUSD spread ($0.30 per oz)
    slippage_dollars: float = 0.10  # Execution slippage ($0.10 per oz)
    commission_per_unit: float = 0.0  # Commission per unit/oz
    risk_pct_per_trade: float = 0.01  # 1% risk per trade
    fixed_units: Optional[float] = None  # Fixed position size if not risk-based

    use_atr_sl_tp: bool = True
    sl_atr_mult: float = 1.5
    tp_atr_mult: float = 3.0
    max_holding_bars: int = 12  # Exit after N bars if neither SL nor TP is hit


@dataclass
class BacktestResult:
    """Summary metrics and trade logs from a completed backtest."""

    initial_capital: float
    final_equity: float
    net_return_pct: float
    total_net_pnl: float

    n_trades: int
    n_wins: int
    n_losses: int
    win_rate: float
    profit_factor: float
    expectancy_dollars: float

    max_drawdown_pct: float
    max_drawdown_dollars: float
    sharpe_ratio: float
    sortino_ratio: float

    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=lambda: pd.Series(dtype=float))
