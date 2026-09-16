"""
XAUUSD AI Trading Research System — Macro Data Store (SQLite)

Provides persistent storage and retrieval for multi-asset macroeconomic
and intermarket time-series (DXY, US10Y, US02Y, TIP, VIX, XAGUSD, BRENT).
"""

import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict
import pandas as pd

logger = logging.getLogger(__name__)

CREATE_MACRO_CANDLES = """
CREATE TABLE IF NOT EXISTS macro_candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    asset_name TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL NOT NULL,
    volume REAL DEFAULT 0,
    UNIQUE(ticker, timestamp)
);
"""

CREATE_MACRO_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_macro_ticker_ts
ON macro_candles(ticker, timestamp);
"""


class MacroDataStore:
    """
    SQLite store for macroeconomic and intermarket time series data.
    """

    def __init__(self, db_path: Optional[str | Path] = None):
        if db_path is None:
            db_path = Path(__file__).resolve().parent / "raw" / "xauusd_research.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(CREATE_MACRO_CANDLES)
            conn.executescript(CREATE_MACRO_INDEXES)
        logger.info("MacroDataStore initialized at %s", self.db_path)

    def store_macro_series(self, ticker: str, asset_name: str, df: pd.DataFrame) -> int:
        """
        Store a historical macro time series DataFrame.
        Expected columns: timestamp, close, and optionally open, high, low, volume.
        """
        if df.empty:
            logger.warning("Empty DataFrame provided for ticker %s, skipping store.", ticker)
            return 0

        df_to_save = df.copy()
        if "timestamp" not in df_to_save.columns:
            if isinstance(df_to_save.index, pd.DatetimeIndex):
                df_to_save = df_to_save.reset_index().rename(columns={"index": "timestamp", "Date": "timestamp"})
            else:
                raise ValueError("DataFrame must contain 'timestamp' column or DatetimeIndex")

        # Format timestamps to ISO UTC strings
        df_to_save["timestamp"] = pd.to_datetime(df_to_save["timestamp"], utc=True).dt.strftime("%Y-%m-%d %H:%M:%S+00:00")

        records = []
        for _, row in df_to_save.iterrows():
            close_val = float(row["close"]) if "close" in row and not pd.isna(row["close"]) else (
                float(row["Close"]) if "Close" in row and not pd.isna(row["Close"]) else None
            )
            if close_val is None:
                continue

            open_val = float(row["open"]) if "open" in row and not pd.isna(row["open"]) else (
                float(row["Open"]) if "Open" in row and not pd.isna(row["Open"]) else close_val
            )
            high_val = float(row["high"]) if "high" in row and not pd.isna(row["high"]) else (
                float(row["High"]) if "High" in row and not pd.isna(row["High"]) else close_val
            )
            low_val = float(row["low"]) if "low" in row and not pd.isna(row["low"]) else (
                float(row["Low"]) if "Low" in row and not pd.isna(row["Low"]) else close_val
            )
            vol_val = float(row["volume"]) if "volume" in row and not pd.isna(row["volume"]) else (
                float(row["Volume"]) if "Volume" in row and not pd.isna(row["Volume"]) else 0.0
            )

            records.append((
                ticker,
                asset_name,
                row["timestamp"],
                open_val,
                high_val,
                low_val,
                close_val,
                vol_val,
            ))

        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO macro_candles
                (ticker, asset_name, timestamp, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )

        logger.info("Stored %d records for macro ticker %s (%s).", len(records), ticker, asset_name)
        return len(records)

    def load_macro_series(
        self,
        ticker: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> pd.DataFrame:
        """
        Load historical macro series for a ticker, sorted ascending by timestamp.
        """
        query = "SELECT timestamp, open, high, low, close, volume FROM macro_candles WHERE ticker = ?"
        params: list = [ticker]

        if start:
            query += " AND timestamp >= ?"
            params.append(start.strftime("%Y-%m-%d %H:%M:%S+00:00") if start.tzinfo else start.isoformat())
        if end:
            query += " AND timestamp <= ?"
            params.append(end.strftime("%Y-%m-%d %H:%M:%S+00:00") if end.tzinfo else end.isoformat())

        query += " ORDER BY timestamp ASC"

        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=params)

        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)

        return df

    def list_available_macro_tickers(self) -> List[Dict[str, str]]:
        """List all stored macro tickers with row counts and date spans."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT ticker, asset_name, COUNT(*), MIN(timestamp), MAX(timestamp)
                FROM macro_candles
                GROUP BY ticker, asset_name
            """)
            rows = cur.fetchall()
            return [
                {
                    "ticker": r[0],
                    "asset_name": r[1],
                    "count": r[2],
                    "start": r[3],
                    "end": r[4],
                }
                for r in rows
            ]
