"""
Dashboard for Phase 5: NLP News Sentiment & Economic Calendar.
Displays upcoming high-impact macroeconomic events and live financial news
with asynchronous background updates and auto-refresh timer.
"""

from datetime import datetime, timezone
from typing import Optional
import pandas as pd
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame
)

from app.workers.news_worker import NewsFetchWorker

AUTO_REFRESH_MS = 300_000  # 5 minutes (polite to FXStreet RSS)


class NewsCalendarPage(QWidget):
    """
    Dashboard for Phase 5: NLP News Sentiment & Economic Calendar.
    Asynchronously fetches upcoming high-impact events and live financial news,
    updating on an automatic timer without freezing the user interface.
    """

    def __init__(self):
        super().__init__()
        self._worker: Optional[NewsFetchWorker] = None
        self._last_updated_str: str = "Never"
        self._remaining_seconds: int = AUTO_REFRESH_MS // 1000

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        self._setup_header()

        # Split Content Layout (Calendar Panel + News Panel)
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(20)

        self._setup_calendar_panel()
        self._setup_news_panel()
        self.main_layout.addLayout(self.content_layout)

        # Setup Auto-Refresh and Countdown Timers
        self.auto_timer = QTimer(self)
        self.auto_timer.setInterval(AUTO_REFRESH_MS)
        self.auto_timer.timeout.connect(self.refresh_data)

        self.countdown_timer = QTimer(self)
        self.countdown_timer.setInterval(1000)
        self.countdown_timer.timeout.connect(self._on_countdown_tick)

        # Start timers and initiate initial data fetch
        self.auto_timer.start(AUTO_REFRESH_MS)
        self.countdown_timer.start(1000)
        self.refresh_data()

    def _setup_header(self):
        header_vbox = QVBoxLayout()
        header_vbox.setSpacing(4)

        header_top = QHBoxLayout()

        title = QLabel("PHASE 5: NLP NEWS & ECONOMIC CALENDAR INTELLIGENCE")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #E0E0E0;")

        self.btn_refresh = QPushButton("REFRESH FEEDS")
        self.btn_refresh.setFixedWidth(150)
        self.btn_refresh.setStyleSheet("""
            QPushButton {
                background-color: #2D333B;
                color: #58A6FF;
                border: 1px solid #444C56;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #373E47; }
            QPushButton:disabled { color: #6E7681; background-color: #1C2128; }
        """)
        self.btn_refresh.clicked.connect(self.refresh_data)

        header_top.addWidget(title)
        header_top.addStretch()
        header_top.addWidget(self.btn_refresh)
        header_vbox.addLayout(header_top)

        self.status_label = QLabel("Initializing live feeds...")
        self.status_label.setStyleSheet("color: #8B949E; font-size: 12px; font-weight: 500;")
        header_vbox.addWidget(self.status_label)

        self.main_layout.addLayout(header_vbox)

    def _setup_calendar_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 6px;")
        layout = QVBoxLayout(panel)

        lbl = QLabel("UPCOMING HIGH-IMPACT EVENTS (RESEARCH SIMULATION)")
        lbl.setStyleSheet("font-weight: bold; color: #8B949E; border: none;")
        layout.addWidget(lbl)

        self.cal_table = QTableWidget(0, 4)
        self.cal_table.setHorizontalHeaderLabels(["Date (UTC)", "Event", "Currency", "Impact"])
        self.cal_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.cal_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.cal_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.cal_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.cal_table.setStyleSheet("""
            QTableWidget {
                background-color: #0D1117;
                color: #C9D1D9;
                gridline-color: #30363D;
                border: none;
            }
            QHeaderView::section {
                background-color: #21262D;
                color: #8B949E;
                padding: 4px;
                border: 1px solid #30363D;
                font-weight: bold;
            }
        """)

        layout.addWidget(self.cal_table)
        self.content_layout.addWidget(panel, stretch=1)

    def _setup_news_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background-color: #161B22; border: 1px solid #30363D; border-radius: 6px;")
        layout = QVBoxLayout(panel)

        lbl = QLabel("LIVE NLP NEWS SENTIMENT (FXSTREET RSS -> TEXTBLOB)")
        lbl.setStyleSheet("font-weight: bold; color: #8B949E; border: none;")
        layout.addWidget(lbl)

        self.news_table = QTableWidget(0, 4)
        self.news_table.setHorizontalHeaderLabels(["Time", "Relevance", "Headline", "Sentiment"])
        self.news_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.news_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.news_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.news_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.news_table.setStyleSheet("""
            QTableWidget {
                background-color: #0D1117;
                color: #C9D1D9;
                gridline-color: #30363D;
                border: none;
            }
            QHeaderView::section {
                background-color: #21262D;
                color: #8B949E;
                padding: 4px;
                border: 1px solid #30363D;
                font-weight: bold;
            }
        """)

        layout.addWidget(self.news_table)
        self.content_layout.addWidget(panel, stretch=2)

    def refresh_data(self):
        """Triggers asynchronous news and calendar fetch in background worker."""
        # Guard against overlapping runs
        if self._worker is not None and self._worker.isRunning():
            return

        self.btn_refresh.setText("UPDATING...")
        self.btn_refresh.setEnabled(False)
        self.status_label.setText("Fetching latest news & calendar events...")

        self._worker = NewsFetchWorker(self)
        self._worker.finished_signal.connect(self._on_fetch_finished)
        self._worker.error_signal.connect(self._on_fetch_error)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.start()

    def _on_fetch_finished(self, news_df: pd.DataFrame, cal_df: pd.DataFrame):
        self.btn_refresh.setText("REFRESH FEEDS")
        self.btn_refresh.setEnabled(True)

        now_utc = datetime.now(timezone.utc)
        self._last_updated_str = now_utc.strftime("%H:%M:%S")
        self._remaining_seconds = AUTO_REFRESH_MS // 1000

        self._populate_tables(news_df, cal_df)

        mins = self._remaining_seconds // 60
        secs = self._remaining_seconds % 60
        self.status_label.setText(
            f"Last updated: {self._last_updated_str} UTC - next refresh in {mins}:{secs:02d}"
        )

    def _on_fetch_error(self, err_msg: str):
        self.btn_refresh.setText("REFRESH FEEDS")
        self.btn_refresh.setEnabled(True)

        now_utc = datetime.now(timezone.utc)
        now_str = now_utc.strftime("%H:%M:%S")

        # Keep existing table data intact — never blank tables on error
        self.status_label.setText(
            f"<font color='#F85149'>Update failed at {now_str} UTC ({err_msg})</font>"
        )
        self._remaining_seconds = AUTO_REFRESH_MS // 1000

    def _on_countdown_tick(self):
        if self._worker is not None and self._worker.isRunning():
            return

        if self._remaining_seconds > 0:
            self._remaining_seconds -= 1

        mins = self._remaining_seconds // 60
        secs = self._remaining_seconds % 60
        if self._last_updated_str != "Never":
            self.status_label.setText(
                f"Last updated: {self._last_updated_str} UTC - next refresh in {mins}:{secs:02d}"
            )

    def _populate_tables(self, news_df: pd.DataFrame, cal_df: pd.DataFrame):
        """Populates calendar and news tables safely with fresh DataFrames."""
        # 1. Update Calendar Table
        if cal_df is not None and not cal_df.empty:
            self.cal_table.setRowCount(len(cal_df))
            for i, (_, row) in enumerate(cal_df.iterrows()):
                dt_str = row["timestamp"].strftime("%Y-%m-%d %H:%M")

                item_date = QTableWidgetItem(dt_str)
                item_event = QTableWidgetItem(str(row["event"]))
                item_ccy = QTableWidgetItem(str(row["currency"]))
                item_impact = QTableWidgetItem(str(row["impact"]))

                item_impact.setForeground(Qt.GlobalColor.red)
                item_impact.setFont(self._bold_font())

                for col_idx, item in enumerate((item_date, item_event, item_ccy, item_impact)):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.cal_table.setItem(i, col_idx, item)

        # 2. Update News Table
        if news_df is not None and not news_df.empty:
            self.news_table.setRowCount(len(news_df))
            for i, (_, row) in enumerate(news_df.iterrows()):
                time_str = row["timestamp"].strftime("%m-%d %H:%M")
                sentiment = float(row["sentiment"])

                item_time = QTableWidgetItem(time_str)
                item_rel = QTableWidgetItem(str(row["relevance"]))
                item_title = QTableWidgetItem(str(row["title"]))

                if sentiment > 0.1:
                    sent_str = f"BULLISH ({sentiment:.2f})"
                    color = "#3FB950"
                elif sentiment < -0.1:
                    sent_str = f"BEARISH ({sentiment:.2f})"
                    color = "#F85149"
                else:
                    sent_str = f"NEUTRAL ({sentiment:.2f})"
                    color = "#8B949E"

                item_sent = QTableWidgetItem(sent_str)
                item_sent.setForeground(QColor(color))
                item_sent.setFont(self._bold_font())

                for col_idx, item in enumerate((item_time, item_rel, item_title, item_sent)):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.news_table.setItem(i, col_idx, item)

    def _bold_font(self) -> QFont:
        f = QFont()
        f.setBold(True)
        return f

    def showEvent(self, event):
        super().showEvent(event)
        # Resume timers when page is shown
        if hasattr(self, "auto_timer") and not self.auto_timer.isActive():
            self.auto_timer.start(AUTO_REFRESH_MS)
        if hasattr(self, "countdown_timer") and not self.countdown_timer.isActive():
            self.countdown_timer.start(1000)

    def hideEvent(self, event):
        super().hideEvent(event)
        # Pause timers when page is hidden to save requests while on other tabs
        if hasattr(self, "auto_timer") and self.auto_timer.isActive():
            self.auto_timer.stop()
        if hasattr(self, "countdown_timer") and self.countdown_timer.isActive():
            self.countdown_timer.stop()

