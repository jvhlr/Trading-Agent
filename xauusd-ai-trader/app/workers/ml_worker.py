"""
Background Worker for Asynchronous ML Model Training & Benchmarking.
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
from models.dataset_builder import build_dataset
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
from models.evaluation import evaluate_classification, evaluate_financial


class MLTrainingWorker(QThread):
    """Worker thread for non-blocking ML model training."""
    progress_signal = Signal(str, int)  # status message, percentage
    finished_signal = Signal(list)     # list of benchmark result dicts
    error_signal = Signal(str)

    def __init__(self, timeframe: str = "H1", days: int = 180, use_synthetic: bool = False):
        super().__init__()
        self.timeframe = timeframe
        self.days = days
        self.use_synthetic = use_synthetic

    def run(self):
        try:
            self.progress_signal.emit("Loading dataset...", 10)
            store = DataStore()
            df = pd.DataFrame()

            if not self.use_synthetic:
                df = store.load_raw(symbol="XAUUSD", timeframe=self.timeframe)

            if df.empty:
                df, _ = generate_sample_data(timeframe=self.timeframe, days=self.days)

            self.progress_signal.emit("Engineering features...", 30)
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

            self.progress_signal.emit("Splitting chronological dataset...", 50)
            ds = build_dataset(
                df,
                feature_cols=feature_cols,
                target_col="target_direction",
                return_col="return_1",
                train_ratio=0.6,
                val_ratio=0.2,
                test_ratio=0.2,
                scale=True,
            )

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

            results = []
            total_models = len(models)

            for idx, model in enumerate(models):
                prog = int(60 + (idx / total_models) * 35)
                self.progress_signal.emit(f"Training {model.name}...", prog)

                model.fit(ds.X_train, ds.y_train)
                preds = model.predict(ds.X_test)
                probs = model.predict_proba(ds.X_test)

                c_metrics = evaluate_classification(ds.y_test, preds, probs)
                f_metrics = evaluate_financial(ds.y_test, preds, ds.returns_test, spread_pct=0.00015)

                results.append({
                    "model_name": model.name,
                    "accuracy": c_metrics.accuracy,
                    "f1_macro": c_metrics.f1_macro,
                    "brier_score": c_metrics.brier_score,
                    "trades": f_metrics.n_trades,
                    "win_rate": f_metrics.win_rate,
                    "net_return_pct": f_metrics.net_return_pct,
                    "profit_factor": f_metrics.profit_factor,
                })

            self.progress_signal.emit("Evaluation complete.", 100)
            self.finished_signal.emit(results)
        except Exception as e:
            self.error_signal.emit(str(e))
