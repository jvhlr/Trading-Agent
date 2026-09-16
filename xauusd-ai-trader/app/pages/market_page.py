"""
Market / Technical Charting Workspace Page.
"""

import json
import logging
import os
from pathlib import Path
from PySide6.QtCore import QUrl, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QComboBox, QCheckBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtWebEngineWidgets import QWebEngineView
import numpy as np
import pandas as pd

from data.data_store import DataStore
from data.data_collector import generate_sample_data

logger = logging.getLogger(__name__)


class MarketPage(QWidget):
    def __init__(self):
        super().__init__()
        self._is_page_loaded = False
        self._pending_payload = None
        self.current_df = None
        self._init_ui()
        self._load_chart_data()
        
        # Auto-refresh timer for live ticking
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._plot_data_only)
        self.timer.start(5000)

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

        self.chart_title = QLabel("<b>XAUUSD Gold Spot Price (H1)</b>")
        chart_layout.addWidget(self.chart_title)

        self.web_view = QWebEngineView()
        template_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates", "tv_candle.html"))
        self.web_view.load(QUrl.fromLocalFile(template_path))
        self.web_view.loadFinished.connect(self._on_web_view_loaded)
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

    def _on_web_view_loaded(self, ok: bool):
        self._is_page_loaded = ok
        if ok and self._pending_payload:
            self.web_view.page().runJavaScript(f"updateData({self._pending_payload})")
            self._pending_payload = None

    def _load_chart_data(self):
        store = DataStore()
        tf = self.tf_combo.currentText()
        df = store.load_raw(symbol="XAUUSD", timeframe=tf, limit=250)
        if df.empty:
            df, _ = generate_sample_data(timeframe=tf, days=30)

        self.current_df = df
        self.chart_title.setText(f"<b>XAUUSD Gold Spot Price ({tf})</b>")
        self._plot_data(fit_content=True)

    def _plot_data_only(self):
        """Poll latest data without changing title or forcing a view reset."""
        store = DataStore()
        tf = self.tf_combo.currentText()
        df = store.load_raw(symbol="XAUUSD", timeframe=tf, limit=250)
        if not df.empty:
            self.current_df = df
        self._plot_data(fit_content=False)

    def _plot_data(self, fit_content=False):
        if getattr(self, "current_df", None) is None or self.current_df.empty:
            return

        df = self.current_df.tail(200).copy()
        
        # Format candle timestamps strictly ascending and unique
        candles = []
        if "timestamp" in df.columns:
            df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
            for i, row in df.iterrows():
                ts = row["timestamp"]
                if hasattr(ts, "timestamp"):
                    time_val = int(ts.timestamp())
                else:
                    try:
                        time_val = int(pd.to_datetime(ts).timestamp())
                    except Exception:
                        time_val = int(i + 1)

                candles.append({
                    "time": time_val,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                })
        else:
            df = df.reset_index(drop=True)
            for i, row in df.iterrows():
                candles.append({
                    "time": int(i + 1),
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                })

        payload = {
            "candles": candles,
            "lines": []
        }

        # SMA Overlays
        if self.chk_sma.isChecked() and len(df) >= 20:
            sma20 = df["close"].rolling(20).mean()
            payload["lines"].append({
                "name": "sma20",
                "color": "#FFD700",
                "width": 2,
                "data": [{"time": c["time"], "value": float(v)} for c, v in zip(candles, sma20) if not pd.isna(v)]
            })
            if len(df) >= 50:
                sma50 = df["close"].rolling(50).mean()
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
                "style": 2,  # Dashed
                "data": [{"time": c["time"], "value": float(v)} for c, v in zip(candles, upper) if not pd.isna(v)]
            })
            payload["lines"].append({
                "name": "bb_lower",
                "color": "#7889A4",
                "style": 2,  # Dashed
                "data": [{"time": c["time"], "value": float(v)} for c, v in zip(candles, lower) if not pd.isna(v)]
            })

        payload["fit_content"] = fit_content

        json_data = json.dumps(payload)
        if self._is_page_loaded:
            self.web_view.page().runJavaScript(f"updateData({json_data})")
        else:
            self._pending_payload = json_data
