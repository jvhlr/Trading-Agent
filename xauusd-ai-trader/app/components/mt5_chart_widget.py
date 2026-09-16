"""
Native MT5 Chart Component using pyqtgraph.
"""

import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPicture, QPainter
import pandas as pd
import numpy as np

from data.data_store import DataStore
from data.mt5_connector import MT5Connector
from config.settings import load_settings

class CandlestickItem(pg.GraphicsObject):
    def __init__(self, data: list[tuple[float, float, float, float, float]]):
        """
        data is a list/array of tuples: (time, open, close, min, max)
        """
        super().__init__()
        self.data = data
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

        for (t, open_p, close_p, min_p, max_p) in self.data:
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
        self.load_data()
        
        # Auto-refresh timer (every 5 seconds)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.poll_data)
        self.timer.start(5000)

    def on_tf_changed(self, tf):
        self.current_timeframe = tf
        self.load_data()

    def poll_data(self):
        """Polls data silently, optionally updating MT5 via collector here or relying on background services."""
        self.load_data()

    def load_data(self):
        df = self.store.load_raw(self.current_symbol, self.current_timeframe, limit=300)
        if df.empty:
            return
        
        # Format for pyqtgraph: (time, open, close, min, max)
        # Using row index for X axis to avoid weekend gaps, then map index to timestamp strings in axis if needed
        data_tuples = []
        for i, row in df.iterrows():
            data_tuples.append((i, row['open'], row['close'], row['low'], row['high']))
            
        if self.candlestick is not None:
            self.plot_widget.removeItem(self.candlestick)
            
        self.candlestick = CandlestickItem(data_tuples)
        self.plot_widget.addItem(self.candlestick)
        
        # Set X axis labels
        def format_time(val, pos):
            idx = int(val)
            if 0 <= idx < len(df):
                return df.iloc[idx]['timestamp'].strftime("%H:%M:%S")
            return ""
            
        axis = self.plot_item.getAxis('bottom')
        # We can't easily dynamically format ticks in standard AxisItem without a custom class, 
        # so for now we leave it as index or we can set specific ticks.
        ticks = [ (i, df.iloc[i]['timestamp'].strftime("%H:%M")) for i in range(0, len(df), max(1, len(df)//10)) ]
        axis.setTicks([ticks])
        
        # Adjust view only if this is the first load or we changed TF
        # self.plot_widget.autoRange()
