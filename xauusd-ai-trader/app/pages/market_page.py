"""
Market / Technical Charting Workspace Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
import pyqtgraph as pg
import numpy as np
import pandas as pd

from data.data_store import DataStore
from data.data_collector import generate_sample_data


class MarketPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._load_chart_data()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── 1. Controls Bar ────────────────────────────────────────────────
        controls_card = QFrame()
        controls_card.setProperty("class", "card")
        c_layout = QHBoxLayout(controls_card)
        c_layout.setContentsMargins(8, 8, 8, 8)

        c_layout.addWidget(QLabel("<b>SYMBOL:</b> XAUUSD"))
        c_layout.addWidget(QLabel(" | "))

        c_layout.addWidget(QLabel("<b>TIMEFRAME:</b>"))
        self.tf_combo = QComboBox()
        self.tf_combo.addItems(["M1", "M5", "M15", "M30", "H1", "H4", "D1"])
        self.tf_combo.setCurrentText("H1")
        self.tf_combo.currentTextChanged.connect(self._load_chart_data)
        c_layout.addWidget(self.tf_combo)

        c_layout.addWidget(QLabel(" | "))
        c_layout.addWidget(QLabel("<b>OVERLAYS:</b>"))

        self.chk_sma = QCheckBox("SMA 20/50")
        self.chk_sma.setChecked(True)
        self.chk_sma.stateChanged.connect(self._plot_data)
        c_layout.addWidget(self.chk_sma)

        self.chk_bb = QCheckBox("Bollinger Bands")
        self.chk_bb.setChecked(True)
        self.chk_bb.stateChanged.connect(self._plot_data)
        c_layout.addWidget(self.chk_bb)

        c_layout.addStretch()

        btn_refresh = QPushButton("REFRESH TICK")
        btn_refresh.clicked.connect(self._load_chart_data)
        c_layout.addWidget(btn_refresh)

        layout.addWidget(controls_card)

        # ── 2. PyQtGraph Interactive Chart ─────────────────────────────────
        chart_card = QFrame()
        chart_card.setProperty("class", "card")
        chart_layout = QVBoxLayout(chart_card)

        pg.setConfigOption("background", "#161920")
        pg.setConfigOption("foreground", "#90A0B7")

        self.plot_widget = pg.PlotWidget(title="XAUUSD Gold Spot Price (H1)")
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setLabel("left", "Price ($/oz)")
        self.plot_widget.setLabel("bottom", "Candle Bar Index")
        chart_layout.addWidget(self.plot_widget)

        layout.addWidget(chart_card, stretch=3)

        # ── 3. Multi-Timeframe Context Table ──────────────────────────────
        mtf_card = QFrame()
        mtf_card.setProperty("class", "card")
        mtf_layout = QVBoxLayout(mtf_card)
        mtf_layout.addWidget(QLabel("MULTI-TIMEFRAME MARKET STRUCTURE CONTEXT"))

        table = QTableWidget(5, 4)
        table.setHorizontalHeaderLabels(["Timeframe", "Role", "State / Signal", "Metrics / Levels"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)

        mtf_data = [
            ("D1", "Longer-Term Macro Trend", "BULLISH", "200 SMA: $3,980.50 | High: $4,350.00"),
            ("H4", "Medium-Term Trend", "BULLISH CONSOLIDATION", "SMA 20 > 50 | ATR: $28.40"),
            ("H1", "Market Structure / Setup", "NEUTRAL (Range-bound)", "Support: $4,275 | Resistance: $4,310"),
            ("M15", "Intraday Setup / Trigger", "BEARISH REJECTION", "RSI: 49.3 | MACD Hist: -2.11"),
            ("M5", "Precision Timing & Entry", "WAIT FOR BREAKOUT", "Spread: 4 pts ($0.40/oz)"),
        ]

        for r, (tf, role, state, metrics) in enumerate(mtf_data):
            table.setItem(r, 0, QTableWidgetItem(tf))
            table.setItem(r, 1, QTableWidgetItem(role))
            table.setItem(r, 2, QTableWidgetItem(state))
            table.setItem(r, 3, QTableWidgetItem(metrics))

        mtf_layout.addWidget(table)
        layout.addWidget(mtf_card, stretch=1)

    def _load_chart_data(self):
        store = DataStore()
        tf = self.tf_combo.currentText()
        df = store.load_raw(symbol="XAUUSD", timeframe=tf)
        if df.empty:
            df, _ = generate_sample_data(timeframe=tf, days=30)

        self.current_df = df
        self._plot_data()

    def _plot_data(self):
        if not hasattr(self, "current_df") or self.current_df.empty:
            return

        self.plot_widget.clear()
        df = self.current_df.tail(150).reset_index(drop=True)
        x = np.arange(len(df))
        close = df["close"].values

        # Price line
        self.plot_widget.plot(x, close, pen=pg.mkPen(color="#00E5FF", width=2), name="Close Price")

        # SMA Overlays
        if self.chk_sma.isChecked() and len(df) >= 50:
            sma20 = df["close"].rolling(20).mean().values
            sma50 = df["close"].rolling(50).mean().values
            self.plot_widget.plot(x, sma20, pen=pg.mkPen(color="#FFD700", width=1.5), name="SMA 20")
            self.plot_widget.plot(x, sma50, pen=pg.mkPen(color="#FF5252", width=1.5), name="SMA 50")

        # Bollinger Bands Overlays
        if self.chk_bb.isChecked() and len(df) >= 20:
            sma20 = df["close"].rolling(20).mean().values
            std20 = df["close"].rolling(20).std().values
            upper = sma20 + 2 * std20
            lower = sma20 - 2 * std20
            self.plot_widget.plot(x, upper, pen=pg.mkPen(color="#7889A4", width=1, style=Qt.DashLine))
            self.plot_widget.plot(x, lower, pen=pg.mkPen(color="#7889A4", width=1, style=Qt.DashLine))
