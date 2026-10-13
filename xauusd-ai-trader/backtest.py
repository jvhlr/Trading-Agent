"""
Phase 3 & Phase 4 Research Backtester & Walk-Forward Validation CLI Terminal.

Executes realistic trade execution simulation on XAUUSD market data.
Accounts for bid/ask spread, slippage, risk budgeting, intra-bar SL/TP,
and macroeconomic regime gating. Generates Research Gate verdict.

Usage:
    py backtest.py                       # synthetic, single holdout
    py backtest.py --real --walk-forward # real data, walk-forward CV
    py backtest.py --no-macro            # disable macro features
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline import load_and_prepare_data
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
from models.trade_freeze_engine import TradeFreezeEngine
from models.dataset_builder import build_dataset
from backtester.backtest_types import BacktestConfig
from backtester.sim import run_backtest
from backtester.walk_forward import run_walk_forward


def _build_model_factories(
    feature_cols: list[str],
    include_macro: bool,
) -> list[tuple[str, object]]:
    """
    Build the list of (name, factory) pairs for the benchmark suite.

    Macro-gated variants are appended only when macro features are available.
    """
    return_idx = feature_cols.index("return_1") if "return_1" in feature_cols else 0
    fast_sma_idx = feature_cols.index("sma_20") if "sma_20" in feature_cols else 0
    slow_sma_idx = feature_cols.index("sma_50") if "sma_50" in feature_cols else 1

    factories: list[tuple[str, object]] = [
        ("Random (Weighted)",    lambda: RandomBaseline(weighted=True, seed=42)),
        ("Majority (Always WAIT)", lambda: MajorityWaitBaseline()),
        ("Momentum (Prev Return)", lambda: PreviousReturnMomentumBaseline(
            return_feature_idx=return_idx
        )),
        ("SMA Crossover",        lambda: SMACrossoverBaseline(
            fast_sma_idx=fast_sma_idx, slow_sma_idx=slow_sma_idx
        )),
        ("Logistic Regression",  lambda: LogisticRegressionModel(C=0.1, random_state=42)),
        ("Random Forest",        lambda: RandomForestModel(
            n_estimators=100, max_depth=4, random_state=42
        )),
        ("Gradient Boosting",    lambda: GradientBoostingModel(
            n_estimators=100, learning_rate=0.03, max_depth=3, random_state=42
        )),
    ]

    if include_macro:
        factories.extend([
            ("Macro-Gated Momentum", lambda: MacroGatedModel(
                PreviousReturnMomentumBaseline(return_feature_idx=return_idx),
                feature_names=feature_cols,
            )),
            ("Macro-Gated Gradient Boosting", lambda: MacroGatedModel(
                GradientBoostingModel(
                    n_estimators=100, learning_rate=0.03, max_depth=3, random_state=42
                ),
                feature_names=feature_cols,
            )),
            ("Macro-Gated Random Forest", lambda: MacroGatedModel(
                RandomForestModel(n_estimators=100, max_depth=4, random_state=42),
                feature_names=feature_cols,
            )),
            ("News-Frozen Macro-Gated GB", lambda: TradeFreezeEngine(
                MacroGatedModel(
                    GradientBoostingModel(
                        n_estimators=100, learning_rate=0.03, max_depth=3, random_state=42
                    ),
                    feature_names=feature_cols,
                ),
                freeze_minutes=30,
            )),
        ])

    return factories


def _run_walk_forward_benchmark(
    df,
    feature_cols: list[str],
    model_factories: list[tuple[str, object]],
    bt_config: BacktestConfig,
) -> str:
    """Run walk-forward cross-validation and print a summary table."""
    print("\n[WALK-FORWARD BENCHMARK SUMMARY]")
    print("=" * 115)
    print(
        f"  {'MODEL NAME':<30} | {'FOLDS':>6} | {'PASS FOLDS':>10} | "
        f"{'OOS TRADES':>10} | {'WIN RATE':>8} | {'NET RETURN':>10} | {'PF':>5}"
    )
    print("=" * 115)

    best_model_name = ""
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
            f"{summary.total_oos_trades:>10d} | {summary.aggregate_win_rate * 100:>7.1f}% | "
            f"{summary.aggregate_net_return_pct * 100:>9.2f}% | "
            f"{summary.aggregate_profit_factor:>5.2f}"
        )

    print("=" * 115)
    return best_model_name, best_net_return


def _run_single_holdout(
    df,
    feature_cols: list[str],
    model_factories: list[tuple[str, object]],
    bt_config: BacktestConfig,
) -> tuple[str, float]:
    """Run single train/test split backtest and print a summary table."""
    print("\n[SINGLE-SPLIT HOLDOUT BACKTEST SUMMARY]")
    print("=" * 130)
    print(
        f"  {'MODEL NAME':<30} | {'FINAL EQUITY':>12} | {'NET RETURN':>10} | "
        f"{'TRADES':>6} | {'WIN RATE':>8} | {'PF':>5} | {'MAX DD':>7} | {'SHARPE':>6}"
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
    test_df = ds.raw_df_cleaned.iloc[-len(ds.X_test) :].reset_index(drop=True)

    best_model_name = ""
    best_net_return = -999.0

    for name, factory in model_factories:
        model = factory()
        if hasattr(model, "set_feature_names"):
            model.set_feature_names(feature_cols)
        model.fit(ds.X_train, ds.y_train)
        preds = model.predict(ds.X_test)

        result = run_backtest(test_df, preds, config=bt_config)

        if result.net_return_pct > best_net_return:
            best_net_return = result.net_return_pct
            best_model_name = name

        print(
            f"  {name:<30} | ${result.final_equity:>11.2f} | "
            f"{result.net_return_pct * 100:>9.2f}% | {result.n_trades:>6d} | "
            f"{result.win_rate * 100:>7.1f}% | {result.profit_factor:>5.2f} | "
            f"{result.max_drawdown_pct * 100:>6.2f}% | {result.sharpe_ratio:>6.2f}"
        )

    print("=" * 130)
    return best_model_name, best_net_return


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
) -> None:
    print("=" * 90)
    print("  XAUUSD AI TRADER -> PHASE 4 MACRO & INTERMARKET RESEARCH BACKTESTER TERMINAL")
    print("=" * 90)
    print(
        f"  Symbol: {symbol} | Timeframe: {timeframe} | "
        f"Capital: $10,000.00 | Days: {days}"
    )
    print(
        f"  Costs: Spread=${spread:.2f}/oz | Slippage=${slippage:.2f}/oz | "
        f"Risk={risk_pct * 100:.1f}% per trade"
    )
    print(
        f"  Macro: {'ENABLED (DXY, Yields, VIX, XAG, Brent)' if include_macro else 'DISABLED'}"
    )
    print(
        f"  Mode: {'Walk-Forward Cross-Validation' if walk_forward else 'Single-Split Holdout'}"
    )
    print("-" * 90)

    # ── Load, validate & engineer features ───────────────────────────────────
    df, feature_cols = load_and_prepare_data(
        synthetic=synthetic,
        days=days,
        timeframe=timeframe,
        symbol=symbol,
        include_macro=include_macro,
        direction_threshold=0.30,
    )

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

    model_factories = _build_model_factories(feature_cols, include_macro)

    # ── Run selected evaluation mode ─────────────────────────────────────────
    if walk_forward:
        best_model_name, best_net_return = _run_walk_forward_benchmark(
            df, feature_cols, model_factories, bt_config
        )
    else:
        best_model_name, best_net_return = _run_single_holdout(
            df, feature_cols, model_factories, bt_config
        )

    # ── Research gate verdict ─────────────────────────────────────────────────
    print("\n[RESEARCH GATE VERDICT]")
    print(f"  Top model  : {best_model_name}")
    print(
        f"  Net return : {best_net_return * 100:.2f}% "
        f"(after spread ${spread:.2f} + slippage ${slippage:.2f})"
    )

    if best_net_return > 0:
        verdict = "PASS — Model demonstrates net profitability after realistic transaction costs."
    else:
        verdict = "INCONCLUSIVE / NO EDGE — Model does NOT overcome transaction costs."

    print(f"\n[PHASE 4 VERDICT] {verdict}")
    print("  Note: Trading remains DISABLED per directive. Fail-closed research mode.")
    print("=" * 90 + "\n")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Phase 4 Macro Research Backtester",
        epilog="Trading is DISABLED. Research-only interface.",
    )
    parser.add_argument(
        "--real",
        action="store_true",
        default=False,
        help="Use stored real MT5 data instead of synthetic",
    )
    parser.add_argument("--days", type=int, default=180, help="Days of data")
    parser.add_argument("--timeframe", type=str, default="H1", help="Candle timeframe")
    parser.add_argument(
        "--spread", type=float, default=0.30, help="Spread in $/oz"
    )
    parser.add_argument(
        "--slippage", type=float, default=0.10, help="Slippage in $/oz"
    )
    parser.add_argument(
        "--risk", type=float, default=0.01, help="Risk fraction per trade (e.g. 0.01)"
    )
    parser.add_argument(
        "--walk-forward",
        action="store_true",
        default=False,
        help="Run walk-forward cross-validation instead of single holdout",
    )
    parser.add_argument(
        "--no-macro",
        action="store_true",
        default=False,
        help="Disable macro/intermarket features",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    run_backtest_terminal(
        synthetic=not args.real,
        days=args.days,
        timeframe=args.timeframe,
        spread=args.spread,
        slippage=args.slippage,
        risk_pct=args.risk,
        walk_forward=args.walk_forward,
        include_macro=not args.no_macro,
    )
