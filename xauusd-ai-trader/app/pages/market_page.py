"""
Market / Technical Charting Workspace Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtWebEngineWidgets import QWebEngineView
import numpy as np
import pandas as pd
import json
import os

from data.data_store import DataStore
from data.data_collector import generate_sample_data

# Removed CandlestickItem


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

        # ── 2. TradingView Interactive Chart ─────────────────────────────────
        chart_card = QFrame()
        chart_card.setProperty("class", "card")
        chart_layout = QVBoxLayout(chart_card)

        self.chart_title = QLabel("<b>XAUUSD Gold Spot Price</b>")
        chart_layout.addWidget(self.chart_title)

        self.web_view = QWebEngineView()
        template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "tv_candle.html")
        self.web_view.load(f"file:///{template_path.replace(chr(92), '/')}")
        chart_layout.addWidget(self.web_view)

        layout.addWidget(chart_card, stretch=3)

        # ── 3. Multi-Timeframe Context Table ──────────────────────────────
        mtf_card = QFrame()
        mtf_card.setProperty("class", "card")
        mtf_layout = QVBoxLayout(mtf_card)
        mtf_layout.addWidget(QLabel("MULTI-TIMEFRAME MARKET STRUCTURE CONTEXT"))

        table = QTableWidget(5, 4)
        table.setHorizontalHeaderLabels(["Timeframe", "Role", "State / Signal", "Metrics / Levels"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
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
        self.chart_title.setText(f"<b>XAUUSD Gold Spot Price ({tf})</b>")
        self._plot_data()

    def _plot_data(self):
        if getattr(self, "current_df", None) is None or self.current_df.empty:
            return

        df = self.current_df.tail(150).reset_index(drop=True)
        
        # Use simple integer indices for the x-axis to match how we display the backtest
        candles = []
        for i in range(len(df)):
            row = df.iloc[i]
            # Convert pandas Timestamp to unix timestamp (seconds) if available, otherwise use index
            time_val = i + 1
            if "timestamp" in df.columns:
                time_val = int(row["timestamp"].timestamp())
                
            candles.append({
                "time": time_val,
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"])
            })

        payload = {
            "candles": candles,
            "lines": []
        }

        # SMA Overlays
        if self.chk_sma.isChecked() and len(df) >= 50:
            sma20 = df["close"].rolling(20).mean()
            sma50 = df["close"].rolling(50).mean()
            
            payload["lines"].append({
                "name": "sma20",
                "color": "#FFD700",
                "width": 2,
                "data": [{"time": c["time"], "value": float(v)} for c, v in zip(candles, sma20) if not pd.isna(v)]
            })
            payload["lines"].append({
                "name": "sma50",
                "color": "#FF5252",
                "width": 2,
                "data": [{"time": c["time"], "value": float(v)} for c, v in zip(candles, sma50) if not pd.isna(v)]
            })

        # Bollinger Bands Overlays
        if self.chk_bb.isChecked() and len(df) >= 20:
            sma20 = df["close"].rolling(20).mean()
            std20 = df["close"].rolling(20).std()
            upper = sma20 + 2 * std20
            lower = sma20 - 2 * std20
            
            payload["lines"].append({
                "name": "bb_upper",
                "color": "#7889A4",
                "style": 2, # Dashed
                "data": [{"time": c["time"], "value": float(v)} for c, v in zip(candles, upper) if not pd.isna(v)]
            })
            payload["lines"].append({
                "name": "bb_lower",
                "color": "#7889A4",
                "style": 2, # Dashed
                "data": [{"time": c["time"], "value": float(v)} for c, v in zip(candles, lower) if not pd.isna(v)]
            })

        json_data = json.dumps(payload)
        self.web_view.page().runJavaScript(f"updateData({json_data})")
