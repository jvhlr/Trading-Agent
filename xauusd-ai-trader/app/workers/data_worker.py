"""
Background Worker for Asynchronous Data Collection & Quality Validation.
"""

from PySide6.QtCore import QThread, Signal
from datetime import datetime, timezone, timedelta
import pandas as pd

from data.mt5_connector import MT5Connector, MT5_AVAILABLE
from data.data_collector import generate_sample_data, collect_historical
from data.data_validator import validate, DataQualityReport
from data.data_store import DataStore


class DataFetchWorker(QThread):
    """Worker thread for non-blocking MT5 or synthetic data collection."""
    finished_signal = Signal(pd.DataFrame, DataQualityReport, str)
    error_signal = Signal(str)

    def __init__(self, timeframe: str = "H1", days: int = 180, use_synthetic: bool = False):
        super().__init__()
        self.timeframe = timeframe
        self.days = days
        self.use_synthetic = use_synthetic

    def run(self):
        try:
            store = DataStore()

            if self.use_synthetic or not MT5_AVAILABLE:
                df, meta = generate_sample_data(timeframe=self.timeframe, days=self.days)
                source = "SYNTHETIC"
            else:
                connector = MT5Connector()
                if not connector.connect():
                    df, meta = generate_sample_data(timeframe=self.timeframe, days=self.days)
                    source = "SYNTHETIC (Fallback)"
                else:
                    symbol_candidates = connector.discover_gold_symbols()
                    broker_symbol = symbol_candidates[0].name if symbol_candidates else "XAUUSD"
                    end = datetime.now(timezone.utc)
                    start = end - timedelta(days=self.days)
                    df, meta = collect_historical(
                        broker_symbol=broker_symbol,
                        timeframe=self.timeframe,
                        start=start,
                        end=end,
                    )
                    connector.disconnect()
                    source = f"MT5 ({broker_symbol})"
                    if df is None or df.empty:
                        df, _ = generate_sample_data(timeframe=self.timeframe, days=self.days)
                        source = "SYNTHETIC (Fallback Empty)"

            report = validate(df, timeframe=self.timeframe)
            dataset_id = store.store_raw(
                df=df,
                symbol="XAUUSD",
                broker_symbol=source,
                timeframe=self.timeframe,
                source=source,
                quality_verdict=report.verdict.name,
            )

            self.finished_signal.emit(df, report, dataset_id)
        except Exception as e:
            self.error_signal.emit(str(e))
