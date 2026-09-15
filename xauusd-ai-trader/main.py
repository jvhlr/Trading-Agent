"""
XAUUSD AI Trading Research System — Research Terminal

Main entry point. Connects to MT5 (or uses stored/synthetic data),
validates data, computes features, and displays a market state summary.

Trading is DISABLED. This is a research-only interface.

Usage:
    py main.py
    py main.py --timeframe H4
    py main.py --synthetic     (use synthetic data for development)
"""

import sys
import logging
import argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root to path so imports work
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from config.settings import load_settings, Settings
from data.mt5_connector import MT5Connector, MT5_AVAILABLE
from data.data_collector import generate_sample_data
from data.data_validator import validate, Verdict
from data.data_store import DataStore
from features.price_features import add_all_price_features
from features.technical_features import add_all_technical_features
from features.structure_features import add_all_structure_features


# ── Logging Setup ────────────────────────────────────────────────────────────

def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the research terminal."""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)

    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / "research_terminal.log", encoding="utf-8"),
        ],
    )


logger = logging.getLogger(__name__)


# ── Market State Display ─────────────────────────────────────────────────────

def display_market_state(
    df: pd.DataFrame,
    settings: Settings,
    data_source: str = "UNKNOWN",
    data_verdict: str = "UNKNOWN",
) -> None:
    """
    Display the research terminal market state summary.

    Format matches the directive's specification.
    """
    if len(df) == 0:
        print("\n  [ERROR] No data available to display.\n")
        return

    latest = df.iloc[-1]
    price = latest.get("close", 0.0)
    broker_sym = settings.symbol.broker_symbol or "NOT CONFIGURED"

    # Trend from different timeframes (we only have one here in V1)
    trend = latest.get("trend", "UNKNOWN")

    # Technical indicators
    atr_col = f"atr_{settings.technical_features.atr_period}"
    rsi_col = f"rsi_{settings.technical_features.rsi_period}"
    atr_val = latest.get(atr_col, float("nan"))
    rsi_val = latest.get(rsi_col, float("nan"))
    spread_val = latest.get("spread", float("nan"))

    # Timestamp
    ts = latest.get("timestamp", "N/A")
    if isinstance(ts, pd.Timestamp):
        ts = ts.strftime("%Y-%m-%d %H:%M:%S UTC")

    # MACD
    macd_val = latest.get("macd", float("nan"))
    macd_hist = latest.get("macd_histogram", float("nan"))

    # Bollinger
    bb_pct_col = f"bb_pct_b_{settings.technical_features.bollinger_period}"
    bb_pct = latest.get(bb_pct_col, float("nan"))

    # ADX
    adx_col = f"adx_{settings.technical_features.adx_period}"
    adx_val = latest.get(adx_col, float("nan"))

    # Momentum via short EMA relationship
    ema12 = latest.get("ema_12", float("nan"))
    ema26 = latest.get("ema_26", float("nan"))
    if pd.notna(ema12) and pd.notna(ema26):
        momentum = "BULLISH" if ema12 > ema26 else "BEARISH" if ema12 < ema26 else "NEUTRAL"
    else:
        momentum = "N/A"

    # Format numbers safely
    def fmt(val, decimals=2):
        if pd.isna(val):
            return "N/A"
        return f"{val:.{decimals}f}"

    output = f"""
========================================
XAUUSD RESEARCH TERMINAL
========================================

Broker Symbol: {broker_sym}

Price: {fmt(price)}

Trend:    {trend}
Momentum: {momentum}

ATR:      {fmt(atr_val)}
RSI:      {fmt(rsi_val, 1)}
MACD:     {fmt(macd_val, 4)} (hist: {fmt(macd_hist, 4)})
ADX:      {fmt(adx_val, 1)}
BB %B:    {fmt(bb_pct, 3)}
Spread:   {fmt(spread_val, 0)}

Data Source:    {data_source}
Data Status:   {data_verdict}
Candles:       {len(df)}
Timestamp:     {ts}

ML:                NOT TRAINED
Macro:             NOT IMPLEMENTED
News:              NOT IMPLEMENTED
Historical Memory: NOT IMPLEMENTED
LLM:               DISABLED

Risk Engine:   RESEARCH ONLY
Trading:       DISABLED

========================================
"""
    print(output)


# ── Main Pipeline ────────────────────────────────────────────────────────────

def run_pipeline(args: argparse.Namespace) -> None:
    """Execute the research terminal pipeline."""
    settings = load_settings()
    setup_logging(settings.log_level)

    logger.info("=" * 60)
    logger.info("XAUUSD Research Terminal starting...")
    logger.info("Trading: DISABLED (system invariant)")
    logger.info("=" * 60)

    # Safety check
    assert not settings.live_trading_enabled, "CRITICAL: Trading must be disabled!"

    timeframe = args.timeframe or settings.research.prediction_timeframe
    data_source = "UNKNOWN"
    quality_verdict = "UNKNOWN"

    # ── Step 1: Acquire data ─────────────────────────────────────────────
    df = None

    if args.synthetic or not MT5_AVAILABLE:
        # Use synthetic data for development
        if not args.synthetic and not MT5_AVAILABLE:
            logger.warning(
                "MT5 not available. Using SYNTHETIC data for development. "
                "This is NOT real market data and must NOT be used for research conclusions."
            )
        df, metadata = generate_sample_data(
            timeframe=timeframe,
            days=args.days,
            internal_symbol=settings.symbol.internal_symbol,
        )
        data_source = "SYNTHETIC — NOT FOR RESEARCH"
    else:
        # Try MT5 connection
        connector = MT5Connector(
            login=settings.mt5.login,
            password=settings.mt5.password,
            server=settings.mt5.server,
            path=settings.mt5.path,
            timeout=settings.mt5.connection_timeout_seconds,
        )

        if connector.connect():
            # Symbol discovery
            candidates = connector.discover_gold_symbols(settings.symbol.gold_search_patterns)
            if candidates:
                # Use first match or configured broker symbol
                broker_sym = settings.symbol.broker_symbol or candidates[0].name
                logger.info("Using broker symbol: %s", broker_sym)

                from data.data_collector import collect_historical
                end = datetime.now(timezone.utc)
                start = end - timedelta(days=args.days)
                df, metadata = collect_historical(
                    connector=connector,
                    broker_symbol=broker_sym,
                    timeframe=timeframe,
                    start=start,
                    end=end,
                )
                data_source = f"MT5 ({broker_sym})"
            else:
                logger.error("No gold symbols found on broker.")

            connector.disconnect()
        else:
            logger.error("MT5 connection failed. Falling back to synthetic data.")
            df, metadata = generate_sample_data(
                timeframe=timeframe,
                days=args.days,
                internal_symbol=settings.symbol.internal_symbol,
            )
            data_source = "SYNTHETIC — MT5 CONNECTION FAILED"

    if df is None or len(df) == 0:
        logger.error("No data available. Cannot proceed.")
        print("\n  [ERROR] No data available. Configure MT5 or use --synthetic.\n")
        return

    # ── Step 2: Validate data ────────────────────────────────────────────
    report = validate(
        df=df,
        timeframe=timeframe,
        symbol=settings.symbol.internal_symbol,
        broker_symbol=data_source,
        max_missing_pct=settings.validation.max_missing_candle_pct,
        max_duplicates=settings.validation.max_duplicate_count,
        max_spread_multiplier=settings.validation.max_spread_multiplier,
        min_price=settings.validation.min_price,
        max_price=settings.validation.max_price,
    )
    quality_verdict = report.verdict.value

    if report.verdict == Verdict.FAIL:
        logger.error("Data validation FAILED. Fix data quality issues before proceeding.")
        print(report)
        return

    # ── Step 3: Store data ───────────────────────────────────────────────
    store = DataStore(settings.data.storage_full_path)
    dataset_id = store.store_raw(
        df=df,
        symbol=settings.symbol.internal_symbol,
        broker_symbol=data_source,
        timeframe=timeframe,
        source=data_source,
        quality_verdict=quality_verdict,
    )
    logger.info("Data stored as dataset %s", dataset_id)

    # ── Step 4: Compute features ─────────────────────────────────────────
    logger.info("Computing features...")

    df = add_all_price_features(
        df,
        rolling_return_periods=settings.price_features.rolling_return_periods,
        rolling_volatility_periods=settings.price_features.rolling_volatility_periods,
    )

    df = add_all_technical_features(
        df,
        sma_periods=settings.technical_features.sma_periods,
        ema_periods=settings.technical_features.ema_periods,
        rsi_period=settings.technical_features.rsi_period,
        macd_fast=settings.technical_features.macd_fast,
        macd_slow=settings.technical_features.macd_slow,
        macd_signal=settings.technical_features.macd_signal,
        atr_period=settings.technical_features.atr_period,
        adx_period=settings.technical_features.adx_period,
        bollinger_period=settings.technical_features.bollinger_period,
        bollinger_std=settings.technical_features.bollinger_std,
    )

    df = add_all_structure_features(
        df,
        swing_lookback=settings.structure_features.swing_lookback,
        trend_sma_period=settings.structure_features.trend_sma_period,
    )

    logger.info("Features computed. Total columns: %d", len(df.columns))

    # ── Step 5: Display market state ─────────────────────────────────────
    display_market_state(
        df=df,
        settings=settings,
        data_source=data_source,
        data_verdict=quality_verdict,
    )


# ── CLI ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="XAUUSD AI Trading Research Terminal — Phase 1",
        epilog="Trading is DISABLED. This is a research-only interface.",
    )
    parser.add_argument(
        "--timeframe", "-tf",
        type=str,
        default=None,
        choices=["M1", "M5", "M15", "H1", "H4", "D1"],
        help="Timeframe for analysis (default: H1 from config)",
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=30,
        help="Number of days of historical data to load (default: 30)",
    )
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use synthetic data for development (NOT for research)",
    )

    args = parser.parse_args()
    run_pipeline(args)


if __name__ == "__main__":
    main()
