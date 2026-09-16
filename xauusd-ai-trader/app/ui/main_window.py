"""
Main Window Shell & Workspace Frame for PySide6 Desktop Workstation.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QListWidget,
    QStackedWidget, QFrame, QLabel, QListWidgetItem, QSizePolicy
)
from PySide6.QtCore import Qt, QSize

from app.pages.overview_page import OverviewPage
from app.pages.market_page import MarketPage
from app.pages.data_page import DataPage
from app.pages.ml_lab_page import MLLabPage
from app.pages.backtest_page import BacktestPage
from app.pages.validation_page import ValidationPage
from app.pages.market_intel_page import MarketIntelPage
from app.pages.memory_page import MemoryPage
from app.pages.decision_pipeline_page import DecisionPipelinePage
from app.pages.small_account_page import SmallAccountPage
from app.pages.risk_page import RiskPage
from app.pages.paper_trading_page import PaperTradingPage
from app.pages.system_logs_page import SystemLogsPage
from app.pages.progress_tracker_page import ProgressTrackerPage
from app.pages.news_calendar_page import NewsCalendarPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("XAUUSD AI Trading Research Workstation — V1.0")
        self.resize(1380, 880)
        self.setMinimumSize(1100, 700)

        self._init_ui()

    def _init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 1. Top Persistent System Status Bar ───────────────────────────
        top_bar = QFrame()
        top_bar.setObjectName("top_bar")
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 0, 16, 0)
        top_layout.setSpacing(10)

        brand_lbl = QLabel("<b>XAUUSD RESEARCH TERMINAL</b>")
        brand_lbl.setStyleSheet("font-size: 13px; font-weight: 800; color: #00E5FF; letter-spacing: 0.5px;")
        top_layout.addWidget(brand_lbl)

        top_layout.addStretch()

        pills = [
            ("MODE:", "RESEARCH", "pill-info"),
            ("MT5:", "CONNECTED", "pill-enabled"),
            ("SYMBOL:", "XAUUSD", "pill-gold"),
            ("DATA:", "UP TO DATE", "pill-info"),
            ("MODEL:", "MOMENTUM_v1.0", "pill-info"),
            ("MARKET:", "OPEN", "pill-enabled"),
            ("RISK:", "LOCKED", "pill-info"),
            ("LIVE TRADING:", "DISABLED", "pill-disabled"),
        ]

        for label_text, val_text, style_cls in pills:
            lbl_key = QLabel(label_text)
            lbl_key.setStyleSheet("color: #7889A4; font-size: 11px; font-weight: 600;")
            lbl_val = QLabel(val_text)
            lbl_val.setProperty("class", f"status-pill {style_cls}")

            top_layout.addWidget(lbl_key)
            top_layout.addWidget(lbl_val)

        root_layout.addWidget(top_bar)

        # ── 2. Sidebar + Stacked Widget Content Body ──────────────────────
        body_widget = QWidget()
        body_layout = QHBoxLayout(body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # Left Sidebar Navigation
        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(210)

        self.pages_stack = QStackedWidget()

        nav_items = [
            ("OVERVIEW", OverviewPage()),
            ("MARKET CHART", MarketPage()),
            ("DATA FOUNDATION", DataPage()),
            ("ML LAB", MLLabPage()),
            ("RESEARCH BACKTEST", BacktestPage()),
            ("VALIDATION", ValidationPage()),
            ("MARKET INTEL", MarketIntelPage()),
            ("NEWS & CALENDAR", NewsCalendarPage()),
            ("HISTORICAL MEMORY", MemoryPage()),
            ("DECISION PIPELINE", DecisionPipelinePage()),
            ("SMALL ACCOUNT ($200)", SmallAccountPage()),
            ("RISK ENGINE", RiskPage()),
            ("PAPER TRADING", PaperTradingPage()),
            ("SYSTEM LOGS", SystemLogsPage()),
            ("PROGRESS TRACKER", ProgressTrackerPage()),
        ]

        for idx, (title, page_widget) in enumerate(nav_items):
            item = QListWidgetItem(title)
            item.setSizeHint(QSize(210, 38))
            self.sidebar.addItem(item)
            self.pages_stack.addWidget(page_widget)

        self.sidebar.currentRowChanged.connect(self.pages_stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        body_layout.addWidget(self.sidebar)
        body_layout.addWidget(self.pages_stack, stretch=1)

        root_layout.addWidget(body_widget)
