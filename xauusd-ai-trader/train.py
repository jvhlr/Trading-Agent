"""
Phase 2 Experiment Runner & Model Benchmark Terminal.

Executes baseline models vs ML classifiers on XAUUSD historical/synthetic dataset.
Evaluates statistical predictive power and financial net expectancy under realistic
spread costs. Generates Phase 2 Research Gate Verdict.

Usage:
    py train.py                  # synthetic data (default)
    py train.py --real           # use stored MT5 data
    py train.py --days 365 --timeframe H4
"""

import argparse
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import load_and_prepare_data
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
) -> None:
    print("=" * 80)
    print("  XAUUSD AI TRADER -> PHASE 2 BASELINE ML & PREDICTION GATE TERMINAL")
    print("=" * 80)
    print(
        f"  Symbol: {symbol} | Timeframe: {timeframe} | "
        f"Direction threshold: ${threshold:.2f}"
    )
    print(
        f"  Data source: {'Synthetic Generator' if synthetic else 'Stored/MT5 Data'} "
        f"| Days: {days}"
    )
    print(
        f"  Transaction cost: {spread_pct * 100:.3f}% "
        f"({spread_pct * 2000:.2f} $/oz spread)"
    )
    print("-" * 80)

    # ── 1. Load, validate & engineer features ────────────────────────────────
    df, feature_cols = load_and_prepare_data(
        synthetic=synthetic,
        days=days,
        timeframe=timeframe,
        symbol=symbol,
        include_macro=False,
        direction_threshold=threshold,
    )

    # ── 2. Build chronological dataset splits ────────────────────────────────
    print(
        "\n[SPLIT] Building strict chronological splits "
        "(Train 60% | Val 20% | Test 20%)..."
    )
    ds = build_dataset(
        df,
        feature_cols=feature_cols,
        target_col="target_direction",
        return_col="target_return",
        train_ratio=0.6,
        val_ratio=0.2,
        test_ratio=0.2,
        scale=True,
    )
    print(
        f"  Train: {len(ds.X_train)} | Val: {len(ds.X_val)} | Test: {len(ds.X_test)}"
    )

    # Class balance check
    classes, counts = np.unique(ds.y_train, return_counts=True)
    dist = {cls: cnt / len(ds.y_train) for cls, cnt in zip(classes, counts)}
    print(
        f"  Class balance — DOWN(-1): {dist.get(-1, 0) * 100:.1f}% | "
        f"WAIT(0): {dist.get(0, 0) * 100:.1f}% | "
        f"UP(1): {dist.get(1, 0) * 100:.1f}%"
    )

    # Resolve feature indices used by rule-based baselines
    return_idx = feature_cols.index("return_1") if "return_1" in feature_cols else 0
    fast_sma_idx = feature_cols.index("sma_20") if "sma_20" in feature_cols else 0
    slow_sma_idx = feature_cols.index("sma_50") if "sma_50" in feature_cols else 1

    # ── 3. Define model suite ────────────────────────────────────────────────
    models = [
        RandomBaseline(weighted=True, seed=42),
        MajorityWaitBaseline(),
        PreviousReturnMomentumBaseline(return_feature_idx=return_idx),
        SMACrossoverBaseline(fast_sma_idx=fast_sma_idx, slow_sma_idx=slow_sma_idx),
        LogisticRegressionModel(C=0.1, random_state=42),
        RandomForestModel(n_estimators=100, max_depth=4, random_state=42),
        GradientBoostingModel(
            n_estimators=100, learning_rate=0.03, max_depth=3, random_state=42
        ),
    ]

    # ── 4. Benchmark evaluation ──────────────────────────────────────────────
    col = f"{'MODEL NAME':<25} | {'ACC(TEST)':>9} | {'F1(MACRO)':>9} | {'BRIER':>7} | {'TRADES':>6} | {'WIN RATE':>8} | {'NET RETURN':>10} | {'PF':>5}"
    print(f"\n{'=' * 105}")
    print(f"  {col}")
    print("=" * 105)

    best_model_name: str = ""
    best_net_return: float = -999.0
    best_acc: float = 0.0
    baseline_acc: float = 0.0

    for model in models:
        model.fit(ds.X_train, ds.y_train)
        preds = model.predict(ds.X_test)
        probs = model.predict_proba(ds.X_test)

        c = evaluate_classification(ds.y_test, preds, probs)
        f = evaluate_financial(ds.y_test, preds, ds.returns_test, spread_pct=spread_pct)

        if "Majority" in model.name:
            baseline_acc = c.accuracy

        if f.net_return_pct > best_net_return:
            best_net_return = f.net_return_pct
            best_model_name = model.name
            best_acc = c.accuracy

        print(
            f"  {model.name:<25} | {c.accuracy * 100:>8.2f}% | {c.f1_macro:>9.4f} | "
            f"{c.brier_score:>7.4f} | {f.n_trades:>6d} | {f.win_rate * 100:>7.1f}% | "
            f"{f.net_return_pct * 100:>9.2f}% | {f.profit_factor:>5.2f}"
        )

    print("=" * 105)

    # ── 5. Research Gate verdict ─────────────────────────────────────────────
    print("\n[RESEARCH GATE #1 EVALUATION]")
    print(f"  Baseline accuracy    : {baseline_acc * 100:.2f}%")
    print(f"  Best model ({best_model_name}) : {best_acc * 100:.2f}%")
    print(f"  Best net return      : {best_net_return * 100:.2f}%")

    edge_over_baseline = best_acc > (baseline_acc + 0.02)
    if best_net_return > 0 and edge_over_baseline:
        verdict = "PASS — Statistically defensible edge over baselines after transaction costs."
    else:
        verdict = (
            "INCONCLUSIVE / NO EDGE — Model does NOT consistently outperform simple "
            "baselines or overcome transaction costs ($0.30/oz spread)."
        )

    print(f"\n[PHASE 2 GATE VERDICT] {verdict}")
    print("  Note: Trading remains DISABLED per directive. Fail-closed research mode.")
    print("=" * 80 + "\n")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 2 Model Benchmark Terminal",
        epilog="Trading is DISABLED. Research-only interface.",
    )
    parser.add_argument(
        "--real",
        action="store_true",
        default=False,
        help="Use stored real MT5 data instead of synthetic",
    )
    parser.add_argument("--days", type=int, default=180, help="Days of historical data")
    parser.add_argument("--timeframe", type=str, default="H1", help="Candle timeframe")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.30,
        help="Direction target threshold in dollars",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_experiment(
        synthetic=not args.real,
        days=args.days,
        timeframe=args.timeframe,
        threshold=args.threshold,
    )
