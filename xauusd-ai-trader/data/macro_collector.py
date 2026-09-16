"""
XAUUSD AI Trading Research System — Macroeconomic & Intermarket Data Collector

Fetches historical and live macroeconomic data (DXY, US10Y, US2Y, TIP, VIX, XAG, BRENT)
from TradingView (primary) or synthetic generator (fallback for offline/testing mode) and stores it in MacroDataStore.

Note: FXStreet is used for news headlines (see news_collector.py). For historical OHLCV
time-series, TradingView remains the primary source as FXStreet does not expose downloadable
historical data via RSS or public API.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd

try:
    from tvDatafeed import TvDatafeed, Interval
    TV_AVAILABLE = True
    # Initialize without login for public data
    tv = TvDatafeed()
except ImportError:
    TV_AVAILABLE = False
    tv = None

from data.macro_data_store import MacroDataStore

logger = logging.getLogger(__name__)

MACRO_TICKER_MAP = {
    "DXY": {"ticker": "DX-Y.NYB", "name": "US Dollar Index", "tv_symbol": "DXY", "tv_exchange": "ICEUS"},
    "US10Y": {"ticker": "^TNX", "name": "US 10-Year Treasury Yield", "tv_symbol": "US10Y", "tv_exchange": "TVC"},
    "US02Y": {"ticker": "^IRX", "name": "US Short-Term Rate Proxy", "tv_symbol": "US02Y", "tv_exchange": "TVC"},
    "TIP": {"ticker": "TIP", "name": "iShares TIPS Bond ETF (Real Yield Proxy)", "tv_symbol": "TIP", "tv_exchange": "AMEX"},
    "VIX": {"ticker": "^VIX", "name": "CBOE Volatility Index", "tv_symbol": "VIX", "tv_exchange": "CBOE"},
    "XAG": {"ticker": "SI=F", "name": "Silver Futures (XAGUSD Proxy)", "tv_symbol": "XAGUSD", "tv_exchange": "OANDA"},
    "BRENT": {"ticker": "BZ=F", "name": "Brent Crude Oil", "tv_symbol": "UKOIL", "tv_exchange": "TVC"},
}


class MacroCollector:
    """
    Collects macroeconomic and cross-market historical series.
    """

    def __init__(self, store: Optional[MacroDataStore] = None):
        self.store = store or MacroDataStore()

    def fetch_macro_series(
        self,
        key: str,
        period: str = "2y",
        interval: str = "1d",
        use_synthetic: bool = False,
    ) -> pd.DataFrame:
        """
        Fetch historical series for a single macro asset.
        """
        if key not in MACRO_TICKER_MAP:
            raise ValueError(f"Unknown macro key: {key}. Available: {list(MACRO_TICKER_MAP.keys())}")

        info = MACRO_TICKER_MAP[key]
        ticker = info["ticker"]
        name = info["name"]

        if use_synthetic:
            df = self.generate_synthetic_macro(key, days=730)
            self.store.store_macro_series(ticker, name, df)
            return df

        # Attempt TradingView first
        if TV_AVAILABLE and tv is not None:
            tv_sym = info.get("tv_symbol")
            tv_exc = info.get("tv_exchange")
            
            try:
                logger.info("Fetching macro data from TradingView for %s (%s:%s)...", key, tv_exc, tv_sym)
                
                tv_interval = Interval.in_daily
                if interval == "1h":
                    tv_interval = Interval.in_1_hour
                    
                n_bars = 730 if interval == "1d" else 5000
                
                tv_data = tv.get_hist(symbol=tv_sym, exchange=tv_exc, interval=tv_interval, n_bars=n_bars)
                
                if tv_data is not None and not tv_data.empty:
                    df = tv_data.copy().reset_index()
                    df.rename(columns={"datetime": "timestamp"}, inplace=True)
                    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
                    
                    for col in ["open", "high", "low", "close", "volume"]:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors="coerce")
                            
                    df = df.dropna(subset=["close"]).sort_values("timestamp").reset_index(drop=True)
                    self.store.store_macro_series(ticker, name, df)
                    logger.info("Successfully fetched %s from TradingView.", key)
                    return df
                else:
                    logger.warning("TradingView returned empty data for %s. Falling back to synthetic.", key)
            except Exception as e:
                logger.warning("Failed to fetch %s from TradingView: %s. Falling back to synthetic.", key, e)

        # Fallback directly to synthetic (FXStreet does not provide historical OHLCV downloads)
        logger.warning("TradingView unavailable for %s. Falling back to synthetic data.", key)
        df = self.generate_synthetic_macro(key, days=730)
        self.store.store_macro_series(ticker, name, df)
        return df

    def fetch_all_macro_series(self, period: str = "2y", use_synthetic: bool = False) -> Dict[str, pd.DataFrame]:
        """Fetch and store all configured macro series."""
        results = {}
        for key in MACRO_TICKER_MAP:
            results[key] = self.fetch_macro_series(key, period=period, use_synthetic=use_synthetic)
        return results

    @staticmethod
    def generate_synthetic_macro(key: str, days: int = 730) -> pd.DataFrame:
        """
        Generate realistic synthetic macro series for deterministic offline testing.
        """
        rng = np.random.default_rng(seed=hash(key) % 2**32)
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(days=days)
        timestamps = pd.date_range(start_time, end_time, freq="1D", tz=timezone.utc)
        n = len(timestamps)

        base_values = {
            "DXY": (103.5, 0.003),
            "US10Y": (4.25, 0.02),
            "US02Y": (4.60, 0.02),
            "TIP": (107.0, 0.004),
            "VIX": (15.0, 0.05),
            "XAG": (31.5, 0.015),
            "BRENT": (82.0, 0.012),
        }
        base, vol = base_values.get(key, (100.0, 0.01))

        if key in ("US10Y", "US02Y"):
            # Mean-reverting yield random walk
            drift = -0.01 * np.arange(n) / n
            innovations = rng.normal(0, vol, n)
            close = np.clip(base + np.cumsum(innovations) + drift, 1.0, 8.0)
        elif key == "VIX":
            # Mean-reverting volatility spikes
            log_vix = np.log(base) + np.cumsum(rng.normal(0, 0.04, n))
            # Occasional spikes
            spikes = (rng.uniform(0, 1, n) > 0.95) * rng.exponential(5.0, n)
            close = np.clip(np.exp(log_vix) + spikes, 10.0, 65.0)
        else:
            # Geometric random walk
            returns = rng.normal(0.0001, vol, n)
            close = base * np.cumprod(1 + returns)

        open_p = close * (1 + rng.normal(0, 0.002, n))
        high_p = np.maximum(open_p, close) * (1 + np.abs(rng.normal(0, 0.004, n)))
        low_p = np.minimum(open_p, close) * (1 - np.abs(rng.normal(0, 0.004, n)))
        volume = rng.integers(10000, 500000, n).astype(float)

        return pd.DataFrame({
            "timestamp": timestamps,
            "open": np.round(open_p, 4),
            "high": np.round(high_p, 4),
            "low": np.round(low_p, 4),
            "close": np.round(close, 4),
            "volume": volume,
        })
