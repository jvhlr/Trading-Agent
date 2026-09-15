"""
Background Worker for Asynchronous Backtesting & Walk-Forward Validation.
"""

from PySide6.QtCore import QThread, Signal
import pandas as pd
import numpy as np

from data.data_store import DataStore
from data.data_collector import generate_sample_data
from features.price_features import add_all_price_features
from features.technical_features import add_all_technical_features
from features.structure_features import add_all_structure_features
from features.label_generator import add_direction_target, add_binary_target

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
from backtester.backtest_types import BacktestConfig
from backtester.walk_forward import run_walk_forward


class BacktestWorker(QThread):
    """Worker thread for non-blocking walk-forward cross-validation."""
    progress_signal = Signal(str, int)
    finished_signal = Signal(list, list)  # results, equity_curve_data
    error_signal = Signal(str)

    def __init__(
        self,
        timeframe: str = "H1",
        days: int = 180,
        use_synthetic: bool = False,
        n_folds: int = 5,
        spread: float = 0.30,
        slippage: float = 0.10,
    ):
        super().__init__()
        self.timeframe = timeframe
        self.days = days
        self.use_synthetic = use_synthetic
        self.n_folds = n_folds
        self.spread = spread
        self.slippage = slippage

    def run(self):
        try:
            self.progress_signal.emit("Loading dataset for backtest...", 10)
            store = DataStore()
            df = pd.DataFrame()

            if not self.use_synthetic:
                df = store.load_raw(symbol="XAUUSD", timeframe=self.timeframe)

            if df.empty:
                df, _ = generate_sample_data(timeframe=self.timeframe, days=self.days)

            self.progress_signal.emit("Computing features...", 30)
            df = add_all_price_features(df)
            df = add_all_technical_features(df)
            df = add_all_structure_features(df)
            df = add_direction_target(df, horizon=1, threshold=0.30)
            df = add_binary_target(df, horizon=1)

            exclude_cols = {
                "timestamp", "open", "high", "low", "close", "tick_volume", "real_volume",
                "spread", "target_direction", "target_return", "target_binary", "structure_trend",
                "swing_high", "swing_low", "swing_high_price", "swing_low_price",
                "prev_swing_high", "prev_swing_low", "swing_pattern_high", "swing_pattern_low"
            }
            feature_cols = [
                c for c in df.columns
                if c not in exclude_cols
                and pd.api.types.is_numeric_dtype(df[c])
                and df[c].iloc[200:].isna().sum() == 0
            ]

            return_idx = feature_cols.index("return_1") if "return_1" in feature_cols else 0
            fast_sma_idx = feature_cols.index("sma_20") if "sma_20" in feature_cols else 0
            slow_sma_idx = feature_cols.index("sma_50") if "sma_50" in feature_cols else 1

            model_factories = [
                lambda: RandomBaseline(weighted=True, seed=42),
                lambda: MajorityWaitBaseline(),
                lambda: PreviousReturnMomentumBaseline(return_feature_idx=return_idx),
                lambda: SMACrossoverBaseline(fast_sma_idx=fast_sma_idx, slow_sma_idx=slow_sma_idx),
                lambda: LogisticRegressionModel(C=0.1, random_state=42),
                lambda: RandomForestModel(n_estimators=100, max_depth=4, random_state=42),
                lambda: GradientBoostingModel(n_estimators=100, learning_rate=0.03, max_depth=3, random_state=42),
            ]

            config = BacktestConfig(
                initial_capital=10000.0,
                risk_pct_per_trade=0.01,
                spread_dollars=self.spread,
                slippage_dollars=self.slippage,
            )

            results = []
            sample_equity_curves = []
            total_models = len(model_factories)
            
            # Dynamic fold sizing for small datasets
            total_bars = len(df)
            if total_bars < 1680:
                train_bars = max(int(total_bars * 0.5), 10)
                val_bars = max(int(total_bars * 0.15), 5)
                test_bars = max(int(total_bars * 0.15), 5)
                step_bars = test_bars
            else:
                train_bars = 1200
                val_bars = 240
                test_bars = 240
                step_bars = 240

            for idx, m_factory in enumerate(model_factories):
                sample_model = m_factory()
                prog = int(40 + (idx / total_models) * 55)
                self.progress_signal.emit(f"Running Walk-Forward CV ({sample_model.name})...", prog)

                wf_result = run_walk_forward(
                    df=df,
                    feature_cols=feature_cols,
                    target_col="target_binary",
                    model_factory=m_factory,
                    train_bars=train_bars,
                    val_bars=val_bars,
                    test_bars=test_bars,
                    step_bars=step_bars,
                    config=config,
                )

                model_equity = [10000.0]
                for fold in wf_result.fold_results:
                    if fold.test_result is not None:
                        eq = fold.test_result.equity_curve
                        if eq is not None and len(eq) > 1:
                            eq_vals = eq.values if hasattr(eq, "values") else eq
                            start_eq = eq_vals[0]
                            for val in eq_vals[1:]:
                                ratio = val / start_eq
                                model_equity.append(model_equity[-1] * ratio)
                
                results.append({
                    "model_name": wf_result.model_name,
                    "folds_tested": wf_result.total_folds,
                    "passed_folds": wf_result.passed_folds,
                    "total_trades": wf_result.total_oos_trades,
                    "win_rate": wf_result.aggregate_win_rate,
                    "net_return_pct": wf_result.aggregate_net_return_pct,
                    "profit_factor": wf_result.aggregate_profit_factor,
                    "max_drawdown": wf_result.max_oos_drawdown_pct,
                    "equity_curve": model_equity,
                })

            self.progress_signal.emit("Walk-Forward Backtest complete.", 100)
            self.finished_signal.emit(results, sample_equity_curves)
        except Exception as e:
            self.error_signal.emit(str(e))
