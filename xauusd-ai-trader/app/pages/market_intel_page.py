"""
Market Intelligence (Cross-Market, Macro, & News Events) Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget
)


class MarketIntelPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()

        # ── Tab 1: Cross-Market Indicators ─────────────────────────────────
        tab_cross = QWidget()
        l_cross = QVBoxLayout(tab_cross)

        grid_xm = QGridLayout()
        xm_cards = [
            ("US DOLLAR INDEX (DXY)", "104.12", "+0.18%", "Inverse correlation to XAUUSD (-0.78)"),
            ("US 10Y TREASURY YIELD", "4.21%", "-0.02%", "Real yield proxy for opportunity cost"),
            ("US 2Y TREASURY YIELD", "4.55%", "+0.01%", "Short-term Fed policy rate expectations"),
            ("CBOE VIX INDEX", "14.85", "-0.45", "Global equity volatility / Safe-haven demand"),
            ("SILVER (XAGUSD)", "$31.40", "+0.82%", "Gold/Silver Ratio: 136.7"),
            ("BRENT CRUDE OIL", "$78.50", "+1.12%", "Energy inflation pressure proxy"),
        ]
        for idx, (title, val, chg, desc) in enumerate(xm_cards):
            card = QFrame()
            card.setProperty("class", "card")
            cl = QVBoxLayout(card)
            cl.addWidget(QLabel(title))
            v_lbl = QLabel(f"<b>{val}</b> <font color='#00E5FF'>({chg})</font>")
            v_lbl.setProperty("class", "card-value")
            cl.addWidget(v_lbl)
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
