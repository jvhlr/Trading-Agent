"""
Walk-Forward Temporal Cross-Validation Engine for XAUUSD Trading System.

Implements rolling/expanding window walk-forward validation:
1. Train model on historical window W_train.
2. Validate/tune on window W_val.
3. Evaluate backtest on completely unseen out-of-sample window W_test.
4. Step forward by step_bars and repeat across all market regimes.
"""

from dataclasses import dataclass, field
from typing import List, Callable, Tuple, Optional
import pandas as pd
import numpy as np

from models.dataset_builder import build_dataset
from models.baselines import BaseModel
from .types import BacktestConfig, BacktestResult, Trade
from .sim import run_backtest


@dataclass
class WalkForwardFoldResult:
    """Out-of-sample result for a single walk-forward fold."""

    fold_index: int
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    val_start: pd.Timestamp
    val_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp

    model_name: str
    n_train_samples: int
    n_test_samples: int
    test_result: BacktestResult


@dataclass
class WalkForwardSummary:
    """Aggregated out-of-sample walk-forward summary performance."""

    model_name: str
    total_folds: int
    passed_folds: int  # Folds with net return > 0
    total_oos_trades: int
    aggregate_net_return_pct: float
    average_fold_return_pct: float
    aggregate_win_rate: float
    aggregate_profit_factor: float
    max_oos_drawdown_pct: float
    fold_results: List[WalkForwardFoldResult] = field(default_factory=list)


def run_walk_forward(
    df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str,
    model_factory: Callable[[], BaseModel],
    train_bars: int = 1200,  # ~50 days of H1 candles
    val_bars: int = 240,     # ~10 days
    test_bars: int = 240,    # ~10 days
    step_bars: int = 240,    # Step forward by 10 days
    config: Optional[BacktestConfig] = None,
) -> WalkForwardSummary:
    """
    Executes rolling window walk-forward backtest analysis.

    Args:
        df: DataFrame containing features, target, price columns.
        feature_cols: List of feature column names.
        target_col: Name of target column (e.g. 'target_direction').
        model_factory: Zero-arg callable returning a fresh BaseModel instance.
        train_bars: Length of training window in bars.
        val_bars: Length of validation window in bars.
        test_bars: Length of test window in bars.
        step_bars: Number of bars to advance each fold step.
        config: BacktestConfig instance.

    Returns:
        WalkForwardSummary object containing aggregated OOS performance.
    """
    if config is None:
        config = BacktestConfig()

    n_samples = len(df)
    window_total = train_bars + val_bars + test_bars

    if n_samples < window_total:
        raise ValueError(
            f"Dataset has {n_samples} bars, but minimum {window_total} required for 1 fold."
        )

    timestamps = (
        df["timestamp"] if "timestamp" in df.columns else pd.Series(df.index)
    )

    fold_results: List[WalkForwardFoldResult] = []
    all_oos_trades: List[Trade] = []
    fold_returns: List[float] = []

    start_idx = 0
    fold_counter = 0

    while start_idx + window_total <= n_samples:
        fold_counter += 1
        train_end_idx = start_idx + train_bars
        val_end_idx = train_end_idx + val_bars
        test_end_idx = val_end_idx + test_bars

        fold_df = df.iloc[start_idx:test_end_idx].reset_index(drop=True)

        # Build chronological dataset split for fold window
        ds = build_dataset(
            fold_df,
            feature_cols=feature_cols,
            target_col=target_col,
            return_col="return_1",
            train_ratio=train_bars / window_total,
            val_ratio=val_bars / window_total,
            test_ratio=test_bars / window_total,
            scale=True,
        )

        # Instantiate fresh model and fit on Train split
        model = model_factory()
        model.fit(ds.X_train, ds.y_train)

        # Predict on Test split (unseen holdout)
        test_preds = model.predict(ds.X_test)

        # Run backtest simulator on Test portion of fold DataFrame
        test_df = fold_df.iloc[-len(ds.X_test):].reset_index(drop=True)
        test_result = run_backtest(test_df, test_preds, config=config)

        fold_res = WalkForwardFoldResult(
            fold_index=fold_counter,
            train_start=timestamps.iloc[start_idx],
            train_end=timestamps.iloc[train_end_idx - 1],
            val_start=timestamps.iloc[train_end_idx],
            val_end=timestamps.iloc[val_end_idx - 1],
            test_start=timestamps.iloc[val_end_idx],
            test_end=timestamps.iloc[test_end_idx - 1],
            model_name=model.name,
            n_train_samples=len(ds.X_train),
            n_test_samples=len(ds.X_test),
            test_result=test_result,
        )

        fold_results.append(fold_res)
        fold_returns.append(test_result.net_return_pct)
        all_oos_trades.extend(test_result.trades)

        # Advance window
        start_idx += step_bars

    # Aggregate OOS statistics
    total_folds = len(fold_results)
    passed_folds = sum(1 for r in fold_returns if r > 0)
    avg_fold_return = float(np.mean(fold_returns)) if fold_returns else 0.0
    agg_return = float(np.sum(fold_returns)) if fold_returns else 0.0

    total_trades = len(all_oos_trades)
    if total_trades > 0:
        pnls = np.array([t.net_pnl for t in all_oos_trades])
        wins = pnls[pnls > 0]
        losses = abs(pnls[pnls < 0])
        agg_win_rate = float(len(wins) / total_trades)
        agg_pf = float(np.sum(wins) / np.sum(losses)) if np.sum(losses) > 0 else (999.0 if np.sum(wins) > 0 else 0.0)
    else:
        agg_win_rate = 0.0
        agg_pf = 0.0

    # Max Drawdown across cumulative fold returns
    cum_returns = np.cumsum(fold_returns)
    running_max = np.maximum.accumulate(cum_returns)
    max_dd = float(np.max(running_max - cum_returns)) if len(running_max) > 0 else 0.0

    sample_model = model_factory()
    return WalkForwardSummary(
        model_name=sample_model.name,
        total_folds=total_folds,
        passed_folds=passed_folds,
        total_oos_trades=total_trades,
        aggregate_net_return_pct=agg_return,
        average_fold_return_pct=avg_fold_return,
        aggregate_win_rate=agg_win_rate,
        aggregate_profit_factor=agg_pf,
        max_oos_drawdown_pct=max_dd,
        fold_results=fold_results,
    )
