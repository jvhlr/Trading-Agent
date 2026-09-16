"""
Phase 3 & Phase 4 Research Backtester & Walk-Forward Validation CLI Terminal.

Executes realistic trade execution simulation on XAUUSD market data.
Accounts for bid/ask spread, slippage, risk budgeting, intra-bar SL/TP, and macroeconomic regime gating.
Generates Phase 4 Out-Of-Sample Research Gate Verdict.
"""

import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np

from data.data_collector import generate_sample_data
from data.data_validator import validate
from features.price_features import add_all_price_features
from features.technical_features import add_all_technical_features
from features.structure_features import add_all_structure_features
from features.macro_features import add_all_macro_features
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
from models.macro_gated_model import MacroGatedModel
from backtester.backtest_types import BacktestConfig
from backtester.sim import run_backtest
from backtester.walk_forward import run_walk_forward


def run_backtest_terminal(
    synthetic: bool = True,
    days: int = 180,
    timeframe: str = "H1",
    symbol: str = "XAUUSD",
    spread: float = 0.30,
    slippage: float = 0.10,
    risk_pct: float = 0.01,
    walk_forward: bool = False,
    include_macro: bool = True,
):
    print("=" * 90)
    print("  XAUUSD AI TRADER -> PHASE 4 MACRO & INTERMARKET RESEARCH BACKTESTER TERMINAL")
    print("=" * 90)
    print(f"  Symbol: {symbol} | Timeframe: {timeframe} | Capital: $10,000.00 | Days: {days}")
    print(f"  Cost Settings: Spread=${spread:.2f}/oz | Slippage=${slippage:.2f}/oz | Risk={risk_pct*100:.1f}% per trade")
    print(f"  Macro Integration: {'ENABLED (DXY, Yields, VIX, XAG, Brent)' if include_macro else 'DISABLED'}")
    print(f"  Mode: {'Walk-Forward Cross-Validation' if walk_forward else 'Single-Split Holdout Backtest'}")
    print("-" * 90)

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
                df, _ = generate_sample_data(timeframe=timeframe, days=days, internal_symbol=symbol)
        except Exception as e:
            print(f"[WARNING] Could not load stored data ({e}), falling back to synthetic dataset.")
            df, _ = generate_sample_data(timeframe=timeframe, days=days, internal_symbol=symbol)

    # 2. Validate Data Quality
    report = validate(df, timeframe=timeframe)
    print(f"\n[DATA QUALITY REPORT] Verdict: {report.verdict.name} | Total bars: {report.row_count}")
    if report.verdict.name == "FAIL":
        print("[FAIL] Data quality validation FAILED. Stopping backtest execution.")
        sys.exit(1)

    # 3. Feature & Label Engineering
    print("\n[FEATURES] Engineering Price, Technical, and Market Structure Features...")
    df = add_all_price_features(df)
    df = add_all_technical_features(df)
    df = add_all_structure_features(df)

    if include_macro:
        print("[FEATURES] Aligning Macro & Intermarket Features (Strict Zero Look-Ahead)...")
        df = add_all_macro_features(df, use_synthetic_fallback=True)

    df = add_direction_target(df, horizon=1, threshold=0.30, target_col="target_direction")

    # Select numerical feature columns
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
        and df[c].iloc[200:].isna().sum() == 0
    ]

    print(f"  Extracted {len(feature_cols)} feature columns for ML modeling.")

    # Configure Backtest Settings
    bt_config = BacktestConfig(
        initial_capital=10_000.0,
        spread_dollars=spread,
        slippage_dollars=slippage,
        risk_pct_per_trade=risk_pct,
        use_atr_sl_tp=True,
        sl_atr_mult=1.5,
        tp_atr_mult=3.0,
        max_holding_bars=12,
    )

    return_idx = feature_cols.index("return_1") if "return_1" in feature_cols else 0
    fast_sma_idx = feature_cols.index("sma_20") if "sma_20" in feature_cols else 0
    slow_sma_idx = feature_cols.index("sma_50") if "sma_50" in feature_cols else 1

    model_factories = [
        ("Random (Weighted)", lambda: RandomBaseline(weighted=True, seed=42)),
        ("Majority (Always WAIT)", lambda: MajorityWaitBaseline()),
        ("Momentum (Prev Return)", lambda: PreviousReturnMomentumBaseline(return_feature_idx=return_idx)),
        ("SMA Crossover", lambda: SMACrossoverBaseline(fast_sma_idx=fast_sma_idx, slow_sma_idx=slow_sma_idx)),
        ("Logistic Regression", lambda: LogisticRegressionModel(C=0.1, random_state=42)),
        ("Random Forest", lambda: RandomForestModel(n_estimators=100, max_depth=4, random_state=42)),
        ("Gradient Boosting", lambda: GradientBoostingModel(n_estimators=100, learning_rate=0.03, max_depth=3, random_state=42)),
    ]

    if include_macro:
        # Add Macro-Gated variants
        model_factories.extend([
            ("Macro-Gated Momentum", lambda: MacroGatedModel(
                PreviousReturnMomentumBaseline(return_feature_idx=return_idx),
                feature_names=feature_cols
            )),
            ("Macro-Gated Gradient Boosting", lambda: MacroGatedModel(
                GradientBoostingModel(n_estimators=100, learning_rate=0.03, max_depth=3, random_state=42),
                feature_names=feature_cols
            )),
            ("Macro-Gated Random Forest", lambda: MacroGatedModel(
                RandomForestModel(n_estimators=100, max_depth=4, random_state=42),
                feature_names=feature_cols
            )),
        ])

    if walk_forward:
        print("\n[WALK-FORWARD BENCHMARK SUMMARY]")
        print("=" * 115)
        print(
            f"  {'MODEL NAME':<30} | {'FOLDS':<6} | {'PASS FOLDS':<10} | {'OOS TRADES':<10} | {'WIN RATE':<8} | {'NET RETURN':<10} | {'PF':<5}"
        )
        print("=" * 115)

        best_model_name = None
        best_net_return = -999.0

        for name, factory in model_factories:
            summary = run_walk_forward(
                df,
                feature_cols=feature_cols,
                target_col="target_direction",
                model_factory=factory,
                train_bars=1200,
                val_bars=240,
                test_bars=240,
                step_bars=240,
                config=bt_config,
            )

            if summary.aggregate_net_return_pct > best_net_return:
                best_net_return = summary.aggregate_net_return_pct
                best_model_name = name

            print(
                f"  {name:<30} | {summary.total_folds:>6d} | {summary.passed_folds:>10d} | "
                f"{summary.total_oos_trades:>10d} | {summary.aggregate_win_rate*100:>7.1f}% | "
                f"{summary.aggregate_net_return_pct*100:>9.2f}% | {summary.aggregate_profit_factor:>5.2f}"
            )

        print("=" * 115)

    else:
        # Single Holdout Backtest
        print("\n[SINGLE-SPLIT HOLDOUT BACKTEST SUMMARY]")
        print("=" * 130)
        print(
            f"  {'MODEL NAME':<30} | {'FINAL EQUITY':<12} | {'NET RETURN':<10} | {'TRADES':<6} | {'WIN RATE':<8} | {'PF':<5} | {'MAX DD':<7} | {'SHARPE':<6}"
        )
        print("=" * 130)

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

        test_df = ds.raw_df_cleaned.iloc[-len(ds.X_test):].reset_index(drop=True)
        best_model_name = None
        best_net_return = -999.0

        for name, factory in model_factories:
            model = factory()
            if hasattr(model, "set_feature_names"):
                model.set_feature_names(feature_cols)
            model.fit(ds.X_train, ds.y_train)
            test_preds = model.predict(ds.X_test)

            result = run_backtest(test_df, test_preds, config=bt_config)

            if result.net_return_pct > best_net_return:
                best_net_return = result.net_return_pct
                best_model_name = name

            print(
                f"  {name:<30} | ${result.final_equity:>11.2f} | {result.net_return_pct*100:>9.2f}% | "
                f"{result.n_trades:>6d} | {result.win_rate*100:>7.1f}% | {result.profit_factor:>5.2f} | "
                f"{result.max_drawdown_pct*100:>6.2f}% | {result.sharpe_ratio:>6.2f}"
            )

        print("=" * 130)

    print("\n[RESEARCH GATE #1 & PHASE 4 VERDICT]")
    print(f"  - Top Performing Model: {best_model_name}")
    print(f"  - Net Return (after spread ${spread:.2f} + slippage ${slippage:.2f}): {best_net_return*100:.2f}%")

    if best_net_return > 0:
        verdict = "PASS -- Model demonstrates net profitability after realistic transaction costs and slippage."
    else:
        verdict = "INCONCLUSIVE / NO EDGE -- Model does NOT overcome transaction costs and slippage."

    print(f"\n[PHASE 4 VERDICT] {verdict}")
    print("  Note: Per directive, trading remains completely DISABLED. Fail-closed research mode.")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 4 Macro Research Backtester")
    parser.add_argument(
        "--real", action="store_true", default=False, help="Use stored real MT5 market data instead of synthetic"
    )
    parser.add_argument("--synthetic", action="store_true", default=False, help="Use synthetic dataset")
    parser.add_argument("--days", type=int, default=180, help="Days of data")
    parser.add_argument("--timeframe", type=str, default="H1", help="Candle timeframe")
    parser.add_argument("--spread", type=float, default=0.30, help="Spread in dollars ($/oz)")
    parser.add_argument("--slippage", type=float, default=0.10, help="Slippage in dollars ($/oz)")
    parser.add_argument("--risk", type=float, default=0.01, help="Risk fraction per trade (e.g. 0.01)")
    parser.add_argument("--walk-forward", action="store_true", default=False, help="Run walk-forward CV")
    parser.add_argument("--no-macro", action="store_true", default=False, help="Disable macro features")
    args = parser.parse_args()

    use_synthetic = not args.real if args.real else True

    run_backtest_terminal(
        synthetic=use_synthetic,
        days=args.days,
        timeframe=args.timeframe,
        spread=args.spread,
        slippage=args.slippage,
        risk_pct=args.risk,
        walk_forward=args.walk_forward,
        include_macro=not args.no_macro,
    )
