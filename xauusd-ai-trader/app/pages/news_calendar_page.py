from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QFrame
)
from PySide6.QtCore import Qt, QTimer
from datetime import datetime, timezone, timedelta
import pandas as pd

from data.news_collector import NewsCollector
from data.calendar_collector import CalendarCollector

class NewsCalendarPage(QWidget):
    """
    Dashboard for Phase 5: NLP News Sentiment & Economic Calendar.
    Displays upcoming high-impact macroeconomic events and live financial news.
    """
    def __init__(self):
        super().__init__()
        self.news_collector = NewsCollector()
        self.calendar_collector = CalendarCollector()
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)
        
        self._setup_header()
        
        # Split Content Layout
        self.content_layout = QHBoxLayout()
        self.content_layout.setSpacing(20)
        
        self._setup_calendar_panel()
        self._setup_news_panel()
        
        self.layout.addLayout(self.content_layout)
        
        # Load data immediately
        self.refresh_data()
        
    def _setup_header(self):
        header_layout = QHBoxLayout()
        
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
        """)
        self.btn_refresh.clicked.connect(self.refresh_data)
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_refresh)
        
        self.layout.addLayout(header_layout)

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
        
        lbl = QLabel("LIVE NLP NEWS SENTIMENT (YFINANCE -> TEXTBLOB)")
        lbl.setStyleSheet("font-weight: bold; color: #8B949E; border: none;")
        layout.addWidget(lbl)
        
        self.news_table = QTableWidget(0, 4)
        self.news_table.setHorizontalHeaderLabels(["Time", "Symbol", "Headline", "Sentiment"])
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
        self.btn_refresh.setText("UPDATING...")
        self.btn_refresh.setEnabled(False)
        
        # We use a short QTimer trick to allow the UI to repaint "UPDATING..." before doing sync blocking tasks.
        # In a real heavy app, this would be a QThread.
        QTimer.singleShot(100, self._do_refresh)
        
    def _do_refresh(self):
        try:
            # 1. Update Calendar
            now = datetime.now(timezone.utc)
            # Show events for the next 60 days
            cal_df = self.calendar_collector.get_events_in_range(now, now + timedelta(days=60))
            
            self.cal_table.setRowCount(len(cal_df))
            for row_idx, row in cal_df.iterrows():
                dt_str = row["timestamp"].strftime("%Y-%m-%d %H:%M")
                
                item_date = QTableWidgetItem(dt_str)
                item_event = QTableWidgetItem(row["event"])
                item_ccy = QTableWidgetItem(row["currency"])
                item_impact = QTableWidgetItem(row["impact"])
                
                item_impact.setForeground(Qt.GlobalColor.red)
                item_impact.setFont(self._bold_font())
                
                for item in (item_date, item_event, item_ccy, item_impact):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.cal_table.setItem(row_idx, item.column(), item)
                    
            # 2. Update News
            news_df = self.news_collector.fetch_latest_news()
            self.news_table.setRowCount(len(news_df))
            
            for row_idx, row in news_df.iterrows():
                time_str = row["timestamp"].strftime("%m-%d %H:%M")
                sentiment = row["sentiment"]
                
                item_time = QTableWidgetItem(time_str)
                item_sym = QTableWidgetItem(row["symbol"])
                item_title = QTableWidgetItem(row["title"])
                
                # Format sentiment
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
                
                # We can set text color via styles, or directly on the item
                # QTableWidgetItem doesn't easily take hex directly via QColor string if not careful, 
                # but we can use PySide6.QtGui.QColor
                from PySide6.QtGui import QColor, QFont
                item_sent.setForeground(QColor(color))
                font = QFont()
                font.setBold(True)
                item_sent.setFont(font)
                
                for col_idx, item in enumerate((item_time, item_sym, item_title, item_sent)):
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.news_table.setItem(row_idx, col_idx, item)
                    
        finally:
            self.btn_refresh.setText("REFRESH FEEDS")
            self.btn_refresh.setEnabled(True)

    def _bold_font(self):
        from PySide6.QtGui import QFont
        f = QFont()
        f.setBold(True)
        return f
