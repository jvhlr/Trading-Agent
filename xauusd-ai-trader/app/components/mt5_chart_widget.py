"""
Native MT5 Chart Component using pyqtgraph.

Maintains a persistent MT5 connection and polls at ~500ms for near-real-time
candlestick updates. Only the last 2 bars are re-fetched on each tick to
minimize overhead; full reloads happen on timeframe changes.
"""

import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPicture, QPainter
import pandas as pd
import numpy as np
import logging

from data.data_store import DataStore
from data.mt5_connector import MT5Connector
from config.settings import load_settings

logger = logging.getLogger(__name__)


class CandlestickItem(pg.GraphicsObject):
    def __init__(self, data: list[tuple[float, float, float, float, float]]):
        """
        data is a list/array of tuples: (time, open, close, min, max)
        """
        super().__init__()
        self._chart_data = data
        self.picture = QPicture()
        self.generatePicture()

    def generatePicture(self):
        self.picture = QPicture()
        p = QPainter(self.picture)
        
        # Colors
        w = 0.3  # Box width
        up_brush = pg.mkBrush('g')
        down_brush = pg.mkBrush('r')
        up_pen = pg.mkPen('g')
        down_pen = pg.mkPen('r')

        for (t, open_p, close_p, min_p, max_p) in self._chart_data:
            if open_p > close_p:
                p.setPen(down_pen)
                p.setBrush(down_brush)
                p.drawLine(pg.QtCore.QPointF(t, min_p), pg.QtCore.QPointF(t, max_p))  # type: ignore
                p.drawRect(QRectF(t - w, open_p, w * 2, close_p - open_p))
            else:
                p.setPen(up_pen)
                p.setBrush(up_brush)
                p.drawLine(pg.QtCore.QPointF(t, min_p), pg.QtCore.QPointF(t, max_p))  # type: ignore
                p.drawRect(QRectF(t - w, open_p, w * 2, close_p - open_p))
                
        p.end()

    def paint(self, painter, option, widget=None):
        painter.drawPicture(0, 0, self.picture)

    def boundingRect(self) -> QRectF:  # type: ignore
        return QRectF(self.picture.boundingRect())

class NativeMT5Chart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.store = DataStore()
        self.settings = load_settings()
        self.current_symbol = self.settings.symbol.internal_symbol
        self.current_timeframe = "M1"  # Default to M1
        
        # Persistent MT5 connection state
        self._mt5_connector: MT5Connector | None = None
        self._broker_symbol: str | None = None
        self._mt5_module = None  # Will hold the MetaTrader5 module
        self._timeframe_map: dict | None = None
        self._cached_df: pd.DataFrame = pd.DataFrame()
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Controls
        ctrl_layout = QHBoxLayout()
        self.lbl_title = QLabel(f"MT5 Live Chart: {self.current_symbol}")
        self.lbl_title.setStyleSheet("font-weight: bold; color: #FFAB00; font-size: 16px;")
        
        self.cb_tf = QComboBox()
        self.cb_tf.addItems(["M1", "M5", "M15", "H1", "H4", "D1"])
        self.cb_tf.currentTextChanged.connect(self.on_tf_changed)
        
        self.btn_refresh = QPushButton("Refresh Now")
        self.btn_refresh.clicked.connect(self.load_data)
        
        ctrl_layout.addWidget(self.lbl_title)
        ctrl_layout.addStretch()
        ctrl_layout.addWidget(QLabel("Timeframe:"))
        ctrl_layout.addWidget(self.cb_tf)
        ctrl_layout.addWidget(self.btn_refresh)
        
        self.main_layout.addLayout(ctrl_layout)
        
        # Plot
        self.plot_widget = pg.PlotWidget(background='#1A1A1A')
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_item = self.plot_widget.getPlotItem()
        self.plot_item.getAxis('bottom').setStyle(tickFont=pg.QtGui.QFont("Arial", 8))
        self.plot_item.getAxis('left').setStyle(tickFont=pg.QtGui.QFont("Arial", 8))
        
        self.main_layout.addWidget(self.plot_widget)  # type: ignore
        
        self.candlestick = None
        
        # Initialize persistent MT5 connection, then do first full load
        self._init_mt5_connection()
        self.load_data()
        
        # Real-time tick timer — 500ms for near-real-time updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._fast_tick)
        self.timer.start(500)

    def _init_mt5_connection(self):
        """Establish a persistent MT5 connection that stays open for the lifetime of this widget."""
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
                    logger.info("NativeMT5Chart: Persistent connection established for %s", self._broker_symbol)
                else:
                    connector.disconnect()
        except Exception as e:
            logger.warning("NativeMT5Chart: Could not init persistent MT5 connection: %s", e)

    def _ensure_mt5(self) -> bool:
        """Re-establish MT5 connection if it dropped."""
        if self._mt5_module is None:
            return False
        # Quick health check
        try:
            info = self._mt5_module.terminal_info()
            if info is not None:
                return True
        except Exception:
            pass
        # Reconnect
        self._init_mt5_connection()
        return self._broker_symbol is not None

    def on_tf_changed(self, tf: str):
        self.current_timeframe = tf
        self.load_data()

    def _fast_tick(self):
        """
        High-frequency tick handler (~500ms). Fetches only the last 2 bars
        from MT5 and surgically updates the cached DataFrame, avoiding a
        full 300-bar re-fetch each cycle.
        """
        if not self._ensure_mt5() or self._broker_symbol is None or self._mt5_module is None:
            return
        
        mt5 = self._mt5_module
        tf_map = self._timeframe_map or {}
        mt5_tf = tf_map.get(self.current_timeframe, mt5.TIMEFRAME_H1)
        
        try:
            # Fetch only last 2 bars (current forming + previous closed)
            rates = mt5.copy_rates_from_pos(self._broker_symbol, mt5_tf, 0, 2)
            if rates is None or len(rates) == 0:
                return
            
            patch_df = pd.DataFrame(rates)
            patch_df["timestamp"] = pd.to_datetime(patch_df["time"], unit="s", utc=True)
            
            if self._cached_df.empty:
                # No cache yet — do a full load instead
                self.load_data()
                return
            
            # Merge: update existing rows by timestamp or append new ones
            for _, new_row in patch_df.iterrows():
                mask = self._cached_df["time"] == new_row["time"]
                if mask.any():
                    # Update in-place (the forming candle changed)
                    idx = self._cached_df.index[mask][0]
                    for col in ["open", "high", "low", "close", "tick_volume", "spread", "real_volume"]:
                        if col in new_row.index and col in self._cached_df.columns:
                            self._cached_df.at[idx, col] = new_row[col]
                else:
                    # New candle appeared — append and trim oldest
                    new_row_df = pd.DataFrame([new_row])
                    self._cached_df = pd.concat([self._cached_df, new_row_df], ignore_index=True)
                    if len(self._cached_df) > 300:
                        self._cached_df = self._cached_df.iloc[-300:].reset_index(drop=True)
            
            self._render_chart(fit_content=False)
            
        except Exception as e:
            logger.debug("NativeMT5Chart fast_tick error: %s", e)

    def load_data(self):
        """Full data load — used on init and timeframe changes."""
        df = pd.DataFrame()
        
        if self._ensure_mt5() and self._broker_symbol is not None and self._mt5_module is not None:
            mt5 = self._mt5_module
            tf_map = self._timeframe_map or {}
            mt5_tf = tf_map.get(self.current_timeframe, mt5.TIMEFRAME_H1)
            rates = mt5.copy_rates_from_pos(self._broker_symbol, mt5_tf, 0, 300)
            if rates is not None and len(rates) > 0:
                df = pd.DataFrame(rates)
                df["timestamp"] = pd.to_datetime(df["time"], unit="s", utc=True)
        
        # Fallback to DataStore if MT5 fails or is missing
        if df.empty:
            df = self.store.load_raw(self.current_symbol, self.current_timeframe, limit=300)
            
        if df.empty:
            return
        
        self._cached_df = df
        self._render_chart(fit_content=True)

    def _render_chart(self, fit_content: bool = False):
        """Render the cached DataFrame as a candlestick chart."""
        df = self._cached_df
        if df.empty:
            return
            
        # Format for pyqtgraph: (index, open, close, low, high)
        data_tuples = []
        for i in range(len(df)):
            row = df.iloc[i]
            data_tuples.append((i, row['open'], row['close'], row['low'], row['high']))
            
        if self.candlestick is not None:
            self.plot_widget.removeItem(self.candlestick)
            
        self.candlestick = CandlestickItem(data_tuples)
        self.plot_widget.addItem(self.candlestick)
        
        # Set X axis labels
        ticks = [(i, df.iloc[i]['timestamp'].strftime("%H:%M")) for i in range(0, len(df), max(1, len(df)//10))]
        axis = self.plot_item.getAxis('bottom')
        axis.setTicks([ticks])
        
        if fit_content:
            self.plot_widget.autoRange()

    def closeEvent(self, event):
        """Clean up persistent MT5 connection on widget close."""
        self.timer.stop()
        if self._mt5_connector is not None:
            try:
                self._mt5_connector.disconnect()
            except Exception:
                pass
        super().closeEvent(event)
