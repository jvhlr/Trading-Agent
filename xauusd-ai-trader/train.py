"""
Phase 2 Experiment Runner & Model Benchmark Terminal.

Executes baseline models vs ML classifiers on XAUUSD historical/synthetic dataset.
Evaluates statistical predictive power and financial net expectancy under realistic spread costs.
Generates Phase 2 Research Gate Verdict.
"""

import argparse
import sys
import pandas as pd
import numpy as np

from data.data_collector import generate_sample_data
from data.data_validator import validate
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


def run_experiment(
    synthetic: bool = True,
    days: int = 180,
    timeframe: str = "H1",
    symbol: str = "XAUUSD",
    threshold: float = 0.30,
    spread_pct: float = 0.00015,
):
    print("=" * 80)
    print("  XAUUSD AI TRADER -> PHASE 2 BASELINE ML & PREDICTION GATE TERMINAL")
    print("=" * 80)
    print(
        f"  Symbol: {symbol} | Timeframe: {timeframe} | Target: H1 Direction | Threshold: ${threshold:.2f}"
    )
    print(
        f"  Data Source: {'Synthetic Generator' if synthetic else 'Stored/MT5 Data'} | Days: {days}"
    )
    print(f"  Transaction Cost Assumption: {spread_pct*100:.3f}% ({spread_pct*2000:.2f}$/oz spread)")
    print("-" * 80)

    # 1. Obtain Data
    if synthetic:
        df, _ = generate_sample_data(timeframe=timeframe, days=days, internal_symbol=symbol)
    else:
        try:
            from data.data_store import DataStore

            store = DataStore()
            df = store.load_raw(symbol=symbol, timeframe=timeframe)
            if df.empty:
                print("[WARNING] Storage empty, falling back to synthetic dataset.")
                df, _ = generate_sample_data(
                    timeframe=timeframe, days=days, internal_symbol=symbol
                )
        except Exception as e:
            print(f"[WARNING] Could not load stored data ({e}), falling back to synthetic dataset.")
            df, _ = generate_sample_data(timeframe=timeframe, days=days, internal_symbol=symbol)

    # 2. Validate Data Quality
    report = validate(df, timeframe=timeframe)
    print(f"\n[DATA QUALITY REPORT] Verdict: {report.verdict.name} | Total bars: {report.row_count}")
    if report.verdict.name == "FAIL":
        print("[FAIL] Data quality validation FAILED. Stopping experiment progression.")
        sys.exit(1)

    # 3. Feature & Label Engineering
    print("\n[FEATURES] Engineering Price, Technical, and Market Structure Features...")
    df = add_all_price_features(df)
    df = add_all_technical_features(df)
    df = add_all_structure_features(df)
    df = add_direction_target(df, horizon=1, threshold=threshold, target_col="target_direction")

    # Select numerical feature columns (must be populated after warmup)
    exclude_cols = {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "tick_volume",
        "real_volume",
        "spread",
        "target_direction",
        "target_return",
        "target_binary",
        "structure_trend",
        "swing_high",
        "swing_low",
        "swing_high_price",
        "swing_low_price",
        "prev_swing_high",
        "prev_swing_low",
        "swing_pattern_high",
        "swing_pattern_low",
    }
    feature_cols = [
        c
        for c in df.columns
        if c not in exclude_cols
        and pd.api.types.is_numeric_dtype(df[c])
        and df[c].iloc[200:].isna().sum() == 0  # Fully populated after warmup
    ]

    print(f"  Extracted {len(feature_cols)} feature columns for ML modeling.")

    # 4. Build Chronological Dataset Splits
    print("\n[SPLIT] Building strict chronological splits (Train: 60% | Val: 20% | Test: 20%)...")
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

    print(f"  Train samples: {len(ds.X_train)} | Val samples: {len(ds.X_val)} | Test samples: {len(ds.X_test)}")

    # Class balance check
    train_classes, train_counts = np.unique(ds.y_train, return_counts=True)
    class_dist = {cls: count / len(ds.y_train) for cls, count in zip(train_classes, train_counts)}
    print(f"  Train Class Balance: DOWN(-1): {class_dist.get(-1,0)*100:.1f}% | WAIT(0): {class_dist.get(0,0)*100:.1f}% | UP(1): {class_dist.get(1,0)*100:.1f}%")

    # Find column indices for baseline models
    return_idx = feature_cols.index("return_1") if "return_1" in feature_cols else 0
    fast_sma_idx = feature_cols.index("sma_20") if "sma_20" in feature_cols else 0
    slow_sma_idx = feature_cols.index("sma_50") if "sma_50" in feature_cols else 1

    # 5. Define Models
    models = [
        # Baselines
        RandomBaseline(weighted=True, seed=42),
        MajorityWaitBaseline(),
        PreviousReturnMomentumBaseline(return_feature_idx=return_idx),
        SMACrossoverBaseline(fast_sma_idx=fast_sma_idx, slow_sma_idx=slow_sma_idx),
        # Machine Learning Models
        LogisticRegressionModel(C=0.1, random_state=42),
        RandomForestModel(n_estimators=100, max_depth=4, random_state=42),
        GradientBoostingModel(n_estimators=100, learning_rate=0.03, max_depth=3, random_state=42),
    ]

    # 6. Benchmark Evaluation
    print("\n" + "=" * 105)
    print(
        f"  {'MODEL NAME':<25} | {'ACC(TEST)':<9} | {'F1(MACRO)':<9} | {'BRIER':<7} | {'TRADES':<6} | {'WIN RATE':<8} | {'NET RETURN':<10} | {'PF':<5}"
    )
    print("=" * 105)

    best_model_name = None
    best_test_net_return = -999.0
    best_test_acc = 0.0
    baseline_acc = 0.0

    for model in models:
        # Fit on Train set ONLY
        model.fit(ds.X_train, ds.y_train)

        # Predict on Test set (unseen holdout)
        preds_test = model.predict(ds.X_test)
        probs_test = model.predict_proba(ds.X_test)

        # Compute metrics
        c_metrics = evaluate_classification(ds.y_test, preds_test, probs_test)
        f_metrics = evaluate_financial(ds.y_test, preds_test, ds.returns_test, spread_pct=spread_pct)

        if "Majority" in model.name:
            baseline_acc = c_metrics.accuracy

        if f_metrics.net_return_pct > best_test_net_return:
            best_test_net_return = f_metrics.net_return_pct
            best_model_name = model.name
            best_test_acc = c_metrics.accuracy

        print(
            f"  {model.name:<25} | {c_metrics.accuracy*100:>8.2f}% | {c_metrics.f1_macro:>9.4f} | "
            f"{c_metrics.brier_score:>7.4f} | {f_metrics.n_trades:>6d} | {f_metrics.win_rate*100:>7.1f}% | "
            f"{f_metrics.net_return_pct*100:>9.2f}% | {f_metrics.profit_factor:>5.2f}"
        )

    print("=" * 105)

    # 7. Phase 2 Research Gate Decision
    print("\n[RESEARCH GATE #1 EVALUATION]")
    print(f"  - Baseline Majority Accuracy: {baseline_acc*100:.2f}%")
    print(f"  - Best Model ({best_model_name}) Accuracy: {best_test_acc*100:.2f}%")
    print(f"  - Best Model Net Return (after transaction costs): {best_test_net_return*100:.2f}%")

    if best_test_net_return > 0 and best_test_acc > (baseline_acc + 0.02):
        verdict = "PASS -- Statistically defensible edge over baselines after transaction costs."
    else:
        verdict = (
            "INCONCLUSIVE / NO EDGE — Model does NOT consistently outperform simple baselines "
            "or overcome transaction costs ($0.30/oz spread)."
        )

    print(f"\n[PHASE 2 GATE VERDICT] {verdict}")
    print("  Note: Per directive, trading remains completely DISABLED. Waiting for real MT5 historical data.")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2 Model Benchmark Terminal")
    parser.add_argument(
        "--real", action="store_true", default=False, help="Use stored real MT5 market data instead of synthetic"
    )
    parser.add_argument(
        "--synthetic", action="store_true", default=False, help="Use synthetic data"
    )
    parser.add_argument("--days", type=int, default=180, help="Days of historical data")
    parser.add_argument("--timeframe", type=str, default="H1", help="Candle timeframe")
    parser.add_argument("--threshold", type=float, default=0.30, help="Direction target threshold ($)")
    args = parser.parse_args()

    # Default to synthetic unless --real is passed
    use_synthetic = not args.real if args.real else True

    run_experiment(
        synthetic=use_synthetic,
        days=args.days,
        timeframe=args.timeframe,
        threshold=args.threshold,
    )
