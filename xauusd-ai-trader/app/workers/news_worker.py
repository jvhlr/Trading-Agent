"""
Background Worker for Asynchronous News & Economic Calendar Data Collection.
"""

import logging
from datetime import datetime, timezone, timedelta
from PySide6.QtCore import QThread, Signal
import pandas as pd

logger = logging.getLogger(__name__)


class NewsFetchWorker(QThread):
    """
    Worker thread for non-blocking FXStreet News and Economic Calendar fetching.
    Instantiates collectors within run() so network calls and computation
    stay completely off the GUI thread.
    """
    finished_signal = Signal(pd.DataFrame, pd.DataFrame)  # (news_df, cal_df)
    error_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

    def run(self):
        try:
            # Build collectors inside the worker thread (not in __init__)
            from data.news_collector import NewsCollector
            from data.calendar_collector import CalendarCollector

            calendar_collector = CalendarCollector()
            news_collector = NewsCollector()

            now = datetime.now(timezone.utc)
            cal_df = calendar_collector.get_events_in_range(now, now + timedelta(days=60))
            news_df = news_collector.fetch_latest_news()

            if news_df is None or news_df.empty:
                self.error_signal.emit("Failed to fetch news feed (no data or connection error)")
                return

            self.finished_signal.emit(news_df, cal_df)
        except Exception as e:
            logger.error(f"NewsFetchWorker error: {e}")
            self.error_signal.emit(str(e))
