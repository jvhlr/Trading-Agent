"""
Market / Technical Charting Workspace Page.

Uses a persistent MT5 connection with 500ms polling for near-real-time
candlestick updates. Only the last 2 bars are re-fetched on each tick;
full reloads happen on timeframe changes.
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
from data.mt5_connector import MT5Connector

logger = logging.getLogger(__name__)


class MarketPage(QWidget):
    def __init__(self):
        super().__init__()
        self._is_page_loaded = False
        self._pending_payload = None
        self.current_df: pd.DataFrame | None = None

        # Persistent MT5 connection state
        self._mt5_connector: MT5Connector | None = None
        self._broker_symbol: str | None = None
        self._mt5_module = None
        self._timeframe_map: dict | None = None

        self._init_ui()
        self._init_mt5_connection()
        self._load_chart_data()
        
        # Real-time tick timer — 500ms for near-real-time updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._fast_tick)
        self.timer.start(500)

    # ─── Persistent MT5 Connection ────────────────────────────────────────

    def _init_mt5_connection(self):
        """Establish a persistent MT5 connection for the lifetime of this page."""
        from data.mt5_connector import MT5_AVAILABLE, TIMEFRAME_MAP
        if not MT5_AVAILABLE:
            return
        try:
            import MetaTrader5 as mt5
            self._mt5_module = mt5
            self._timeframe_map = TIMEFRAME_MAP

            connector = MT5Connector()
            if connector.connect():
                symbol_candidates = connector.discover_gold_symbols()
                if symbol_candidates:
                    self._broker_symbol = symbol_candidates[0].name
                    self._mt5_connector = connector
                    logger.info("MarketPage: Persistent MT5 connection for %s", self._broker_symbol)
                else:
                    connector.disconnect()
        except Exception as e:
            logger.warning("MarketPage: Could not init persistent MT5: %s", e)

    def _ensure_mt5(self) -> bool:
        """Re-establish connection if it dropped."""
        if self._mt5_module is None:
            return False
        try:
            info = self._mt5_module.terminal_info()
            if info is not None:
                return True
        except Exception:
            pass
        self._init_mt5_connection()
        return self._broker_symbol is not None

    # ─── UI Setup ─────────────────────────────────────────────────────────

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

    # ─── Data Loading ─────────────────────────────────────────────────────

    def _load_chart_data(self):
        """Full data load — used on init and timeframe changes."""
        tf = self.tf_combo.currentText()
        df = pd.DataFrame()

        if self._ensure_mt5() and self._broker_symbol is not None:
            mt5 = self._mt5_module
            tf_map = self._timeframe_map or {}
            mt5_tf = tf_map.get(tf, mt5.TIMEFRAME_H1)
            rates = mt5.copy_rates_from_pos(self._broker_symbol, mt5_tf, 0, 250)
            if rates is not None and len(rates) > 0:
                df = pd.DataFrame(rates)
                df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)

        if df.empty:
            store = DataStore()
            df = store.load_raw(symbol="XAUUSD", timeframe=tf, limit=250)
        if df.empty:
            df, _ = generate_sample_data(timeframe=tf, days=30)

        self.current_df = df
        self.chart_title.setText(f"<b>XAUUSD Gold Spot Price ({tf})</b>")
        self._plot_data(fit_content=True)

    def _fast_tick(self):
        """
        High-frequency tick handler (~500ms). Fetches only the last 2 bars
        and surgically patches the cached DataFrame.
        """
        if not self._ensure_mt5() or self._broker_symbol is None:
            return
        if self.current_df is None or self.current_df.empty:
            return

        mt5 = self._mt5_module
        tf = self.tf_combo.currentText()
        tf_map = self._timeframe_map or {}
        mt5_tf = tf_map.get(tf, mt5.TIMEFRAME_H1)

        try:
            rates = mt5.copy_rates_from_pos(self._broker_symbol, mt5_tf, 0, 2)
            if rates is None or len(rates) == 0:
                return

            patch_df = pd.DataFrame(rates)
            patch_df["timestamp"] = pd.to_datetime(patch_df["time"], unit="s", utc=True)

            df = self.current_df
            changed = False

            for _, new_row in patch_df.iterrows():
                if "time" not in df.columns:
                    break
                mask = df["time"] == new_row["time"]
                if mask.any():
                    idx = df.index[mask][0]
                    for col in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
                        if col in new_row.index and col in df.columns:
                            df.at[idx, col] = new_row[col]
                    changed = True
                else:
                    new_row_df = pd.DataFrame([new_row])
                    df = pd.concat([df, new_row_df], ignore_index=True)
                    if len(df) > 250:
                        df = df.iloc[-250:].reset_index(drop=True)
                    changed = True

            if changed:
                self.current_df = df
                self._plot_data(fit_content=False)

        except Exception as e:
            logger.debug("MarketPage fast_tick error: %s", e)

    # ─── Chart Rendering ──────────────────────────────────────────────────

    def _plot_data(self, fit_content=False):
        if self.current_df is None or self.current_df.empty:
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

        payload: dict = {
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

    def closeEvent(self, event):
        """Clean up persistent MT5 connection on widget close."""
        self.timer.stop()
        if self._mt5_connector is not None:
            try:
                self._mt5_connector.disconnect()
            except Exception:
                pass
        super().closeEvent(event)
