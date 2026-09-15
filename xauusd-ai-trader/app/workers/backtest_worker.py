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
from features.label_generator import add_direction_target

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

            models = [
                RandomBaseline(weighted=True, seed=42),
                MajorityWaitBaseline(),
                PreviousReturnMomentumBaseline(return_feature_idx=return_idx),
                SMACrossoverBaseline(fast_sma_idx=fast_sma_idx, slow_sma_idx=slow_sma_idx),
                LogisticRegressionModel(C=0.1, random_state=42),
                RandomForestModel(n_estimators=100, max_depth=4, random_state=42),
                GradientBoostingModel(n_estimators=100, learning_rate=0.03, max_depth=3, random_state=42),
            ]

            config = BacktestConfig(
                initial_capital=10000.0,
                risk_pct_per_trade=0.01,
                spread_dollars=self.spread,
                slippage_dollars=self.slippage,
            )

            results = []
            sample_equity_curves = []
            total_models = len(models)

            for idx, model in enumerate(models):
                prog = int(40 + (idx / total_models) * 55)
                self.progress_signal.emit(f"Running Walk-Forward CV ({model.name})...", prog)

                wf_result = run_walk_forward(
                    df=df,
                    model=model,
                    feature_cols=feature_cols,
                    n_folds=self.n_folds,
                    config=config,
                )

                results.append({
                    "model_name": model.name,
                    "folds_tested": wf_result.n_folds,
                    "passed_folds": wf_result.passed_folds,
                    "total_trades": wf_result.total_trades,
                    "win_rate": wf_result.win_rate,
                    "net_return_pct": wf_result.overall_net_return_pct,
                    "profit_factor": wf_result.overall_profit_factor,
                })

            self.progress_signal.emit("Walk-Forward Backtest complete.", 100)
            self.finished_signal.emit(results, sample_equity_curves)
        except Exception as e:
            self.error_signal.emit(str(e))
