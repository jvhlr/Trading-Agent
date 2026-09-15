"""
XAUUSD AI Trading Research System — Data Store (SQLite)

Provides persistent storage for raw candle data and dataset version
tracking. Uses SQLite for simplicity in the research phase.

Key design decisions:
- Raw data is stored as-is (no transformation on write)
- Dataset versions are immutable once created
- No silent overwriting of datasets used in experiments
"""

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


# ── Schema Definitions ───────────────────────────────────────────────────────

CREATE_RAW_CANDLES = """
CREATE TABLE IF NOT EXISTS raw_candles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    broker_symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    tick_volume INTEGER DEFAULT 0,
    spread INTEGER DEFAULT 0,
    real_volume INTEGER DEFAULT 0,
    UNIQUE(dataset_id, symbol, timeframe, timestamp)
);
"""

CREATE_DATASET_VERSIONS = """
CREATE TABLE IF NOT EXISTS dataset_versions (
    dataset_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    broker_symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    source TEXT NOT NULL,
    processing_version TEXT DEFAULT '1.0',
    feature_version TEXT DEFAULT NULL,
    quality_verdict TEXT DEFAULT 'UNKNOWN',
    notes TEXT DEFAULT ''
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_candles_symbol_tf_ts
ON raw_candles(symbol, timeframe, timestamp);

CREATE INDEX IF NOT EXISTS idx_candles_dataset
ON raw_candles(dataset_id);
"""


class DataStore:
    """
    SQLite-backed data store for XAUUSD research data.

    Provides:
    - store_raw(): Save a DataFrame with dataset versioning
    - load_raw(): Retrieve stored data by symbol/timeframe/date range
    - get_dataset_info(): Retrieve version metadata
    - list_datasets(): List all stored dataset versions
    """

    def __init__(self, db_path: str | Path | None = None):
        """
        Initialize the data store.

        Args:
            db_path: Path to the SQLite database file. Defaults to data/raw/xauusd_research.db.
        """
        if db_path is None:
            db_path = Path(__file__).resolve().parent / "raw" / "xauusd_research.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Create tables and indexes if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(CREATE_RAW_CANDLES)
            conn.executescript(CREATE_DATASET_VERSIONS)
            conn.executescript(CREATE_INDEXES)
        logger.info("Database initialized at %s", self.db_path)

    def store_raw(
        self,
        df: pd.DataFrame,
        symbol: str,
        broker_symbol: str,
        timeframe: str,
        source: str = "MT5",
        quality_verdict: str = "UNKNOWN",
        notes: str = "",
    ) -> str:
        """
        Store raw candle data with a new dataset version.

        Args:
            df: DataFrame with columns: timestamp, open, high, low, close,
                and optionally: tick_volume, spread, real_volume.
            symbol: Internal symbol name (e.g., 'XAUUSD').
            broker_symbol: Broker's symbol name.
            timeframe: Timeframe string (e.g., 'H1').
            source: Data source identifier.
            quality_verdict: Result from data validation.
            notes: Any notes about this dataset.

        Returns:
            The dataset_id for this stored version.

        Raises:
            ValueError: If the DataFrame is empty or missing required columns.
        """
        required_cols = {"timestamp", "open", "high", "low", "close"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"DataFrame missing required columns: {missing}")

        if len(df) == 0:
            raise ValueError("Cannot store empty DataFrame.")

        dataset_id = str(uuid.uuid4())[:12]
        created_at = datetime.now(timezone.utc).isoformat()

        # Prepare candle rows
        records = []
        for _, row in df.iterrows():
            ts = row["timestamp"]
            if isinstance(ts, pd.Timestamp):
                ts = ts.isoformat()
            records.append((
                dataset_id,
                symbol,
                broker_symbol,
                timeframe,
                str(ts),
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                int(row.get("tick_volume", 0)),
                int(row.get("spread", 0)),
                int(row.get("real_volume", 0)),
            ))

        # Write to database
        with sqlite3.connect(self.db_path) as conn:
            # Insert candles
            conn.executemany(
                """
                INSERT INTO raw_candles
                (dataset_id, symbol, broker_symbol, timeframe, timestamp,
                 open, high, low, close, tick_volume, spread, real_volume)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                records,
            )

            # Insert dataset version
            conn.execute(
                """
                INSERT INTO dataset_versions
                (dataset_id, symbol, broker_symbol, timeframe,
                 start_date, end_date, row_count, created_at,
                 source, quality_verdict, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    dataset_id, symbol, broker_symbol, timeframe,
                    str(df["timestamp"].min()),
                    str(df["timestamp"].max()),
                    len(df),
                    created_at,
                    source,
                    quality_verdict,
                    notes,
                ),
            )

        logger.info(
            "Stored %d candles as dataset %s (%s %s %s).",
            len(df), dataset_id, symbol, timeframe, source,
        )

        return dataset_id

    def load_raw(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        dataset_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Load stored candle data.

        Args:
            symbol: Internal symbol name.
            timeframe: Timeframe string.
            start: Optional start datetime filter.
            end: Optional end datetime filter.
            dataset_id: Optional specific dataset version to load.

        Returns:
            DataFrame with candle data, or empty DataFrame if not found.
        """
        if not dataset_id:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT dataset_id FROM dataset_versions WHERE symbol = ? AND timeframe = ? ORDER BY created_at DESC LIMIT 1",
                    (symbol, timeframe),
                )
                row = cur.fetchone()
                if row:
                    dataset_id = row[0]

        query = "SELECT timestamp, open, high, low, close, tick_volume, spread, real_volume FROM raw_candles WHERE symbol = ? AND timeframe = ?"
        params: list = [symbol, timeframe]

        if dataset_id:
            query += " AND dataset_id = ?"
            params.append(dataset_id)
        if start:
            query += " AND timestamp >= ?"
            params.append(start.isoformat())
        if end:
            query += " AND timestamp <= ?"
            params.append(end.isoformat())

        query += " ORDER BY timestamp ASC"

        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql_query(query, conn, params=params)

        if len(df) > 0:
            df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
            logger.info(
                "Loaded %d candles (%s %s, %s → %s).",
                len(df), symbol, timeframe,
                df["timestamp"].min(), df["timestamp"].max(),
            )
        else:
            logger.warning("No data found for %s %s with given filters.", symbol, timeframe)

        return df

    def get_dataset_info(self, dataset_id: str) -> Optional[dict]:
        """Retrieve metadata for a specific dataset version."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM dataset_versions WHERE dataset_id = ?",
                (dataset_id,),
            ).fetchone()

        if row is None:
            return None
        return dict(row)

    def list_datasets(self, symbol: Optional[str] = None) -> list[dict]:
        """List all stored dataset versions, optionally filtered by symbol."""
        query = "SELECT * FROM dataset_versions"
        params: list = []
        if symbol:
            query += " WHERE symbol = ?"
            params.append(symbol)
        query += " ORDER BY created_at DESC"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query, params).fetchall()

        return [dict(row) for row in rows]

    def get_latest_dataset_id(self, symbol: str, timeframe: str) -> Optional[str]:
        """Get the most recent dataset_id for a symbol + timeframe."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """
                SELECT dataset_id FROM dataset_versions
                WHERE symbol = ? AND timeframe = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (symbol, timeframe),
            ).fetchone()

        return row[0] if row else None
