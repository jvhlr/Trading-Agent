from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QPushButton, QProgressBar
)
from PySide6.QtCore import Qt

from app.workers.macro_worker import MacroFetchWorker

class MarketIntelPage(QWidget):
    def __init__(self):
        super().__init__()
        self.xm_labels = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()

        # ── Tab 1: Cross-Market Indicators ─────────────────────────────────
        tab_cross = QWidget()
        l_cross = QVBoxLayout(tab_cross)
        
        # Add Refresh Button and Progress Bar
        header_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("REFRESH MACRO DATA (Yahoo Finance)")
        self.btn_refresh.clicked.connect(self._start_fetch)
        self.btn_refresh.setMinimumHeight(40)
        self.btn_refresh.setStyleSheet("background-color: #00E5FF; color: #0D1117; font-weight: bold; border-radius: 4px;")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        
        header_layout.addWidget(self.btn_refresh)
        header_layout.addWidget(self.progress_bar)
        l_cross.addLayout(header_layout)

        grid_xm = QGridLayout()
        # Internal Key -> (Title, Description)
        xm_cards = {
            "DXY": ("US DOLLAR INDEX (DXY)", "Inverse correlation to XAUUSD (-0.78)"),
            "US10Y": ("US 10Y TREASURY YIELD", "Real yield proxy for opportunity cost"),
            "US2Y": ("US 2Y TREASURY YIELD", "Short-term Fed policy rate expectations"),
            "VIX": ("CBOE VIX INDEX", "Global equity volatility / Safe-haven demand"),
            "XAG": ("SILVER (XAGUSD)", "Gold/Silver Ratio proxy"),
            "BRENT": ("BRENT CRUDE OIL", "Energy inflation pressure proxy"),
        }
        
        for idx, (key, (title, desc)) in enumerate(xm_cards.items()):
            card = QFrame()
            card.setProperty("class", "card")
            cl = QVBoxLayout(card)
            cl.addWidget(QLabel(title))
            
            # Value label
            v_lbl = QLabel("<b>N/A</b> <font color='#90A0B7'>(Loading...)</font>")
            v_lbl.setProperty("class", "card-value")
            cl.addWidget(v_lbl)
            self.xm_labels[key] = v_lbl
            
            cl.addWidget(QLabel(desc))
            r, c = divmod(idx, 3)
            grid_xm.addWidget(card, r, c)

        l_cross.addLayout(grid_xm)
        tabs.addTab(tab_cross, "CROSS-MARKET INDICATORS")

        # ── Tab 2: Macro Calendar & Releases ────────────────────────────────
        tab_macro = QWidget()
        l_macro = QVBoxLayout(tab_macro)

        t_macro = QTableWidget(6, 7)
        t_macro.setHorizontalHeaderLabels([
            "Release Time (UTC)", "Event Name", "Country", "Previous", "Forecast", "Actual", "Gold Impact"
        ])
        t_macro.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        t_macro.verticalHeader().setVisible(False)

        macro_data = [
            ("2026-09-16 12:30", "US CPI MoM", "USA", "0.2%", "0.2%", "0.3%", "HIGH (Dollar Rally / Gold Drop)"),
            ("2026-09-16 12:30", "US Core CPI YoY", "USA", "3.2%", "3.2%", "3.3%", "HIGH"),
            ("2026-09-18 18:00", "FOMC Rate Decision", "USA", "5.25%", "5.00%", "Pending", "CRITICAL"),
            ("2026-09-20 12:30", "US Retail Sales MoM", "USA", "0.4%", "0.3%", "Pending", "MEDIUM"),
            ("2026-09-25 12:30", "Core PCE Price Index", "USA", "0.2%", "0.2%", "Pending", "HIGH"),
            ("2026-10-02 12:30", "Non-Farm Payrolls (NFP)", "USA", "142K", "165K", "Pending", "CRITICAL"),
        ]

        for r, row in enumerate(macro_data):
            for c, val in enumerate(row):
                t_macro.setItem(r, c, QTableWidgetItem(val))

        l_macro.addWidget(t_macro)
        tabs.addTab(tab_macro, "MACROECONOMIC CALENDAR")

        layout.addWidget(tabs)
        
        # Trigger an initial fetch
        self._start_fetch()

    def _start_fetch(self):
        self.btn_refresh.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        
        self.worker = MacroFetchWorker()
        self.worker.finished_signal.connect(self._on_fetch_finished)
        self.worker.error_signal.connect(self._on_fetch_error)
        self.worker.start()

    def _on_fetch_finished(self, results):
        self.progress_bar.setVisible(False)
        self.btn_refresh.setEnabled(True)
        
        for key, data in results.items():
            if key in self.xm_labels:
                val = data.get("val", "N/A")
                chg = data.get("chg", "N/A")
                
                # Determine color based on sign
                color = "#90A0B7"
                if chg.startswith("+"):
                    color = "#00E676"
                elif chg.startswith("-"):
                    color = "#FF5252"
                    
                self.xm_labels[key].setText(f"<b>{val}</b> <font color='{color}'>({chg})</font>")

    def _on_fetch_error(self, err_msg):
        self.progress_bar.setVisible(False)
        self.btn_refresh.setEnabled(True)
