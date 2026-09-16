"""
Market Intelligence & Cross-Market / Macroeconomic Dashboard.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QPushButton, QProgressBar
)
from PySide6.QtCore import Qt
import pandas as pd
import numpy as np

from app.workers.macro_worker import MacroFetchWorker
from app.components.tradingview_widget import TradingViewWidget
from features.macro_features import add_all_macro_features, MacroRegime
from data.data_store import DataStore
from data.data_collector import generate_sample_data


class MarketIntelPage(QWidget):
    def __init__(self):
        super().__init__()
        self.xm_labels = {}
        self.regime_labels = {}
        self._init_ui()
        self._load_macro_regimes()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        tabs = QTabWidget()

        # ── Tab 0: TradingView Charts ──────────────────────────────────────
        tab_charts = QWidget()
        l_charts = QVBoxLayout(tab_charts)
        self.tv_widget = TradingViewWidget(symbol="OANDA:XAUUSD", interval="60")
        l_charts.addWidget(self.tv_widget)
        tabs.addTab(tab_charts, "TRADINGVIEW CHARTS")

        # ── Tab 1: Cross-Market Indicators ─────────────────────────────────
        tab_cross = QWidget()
        l_cross = QVBoxLayout(tab_cross)

        # Refresh Header
        header_layout = QHBoxLayout()
        self.btn_refresh = QPushButton("REFRESH MACRO DATA (Yahoo Finance)")
        self.btn_refresh.clicked.connect(self._start_fetch)
        self.btn_refresh.setMinimumHeight(38)
        self.btn_refresh.setProperty("class", "primary")

        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)

        header_layout.addWidget(self.btn_refresh)
        header_layout.addWidget(self.progress_bar)
        l_cross.addLayout(header_layout)

        grid_xm = QGridLayout()
        grid_xm.setSpacing(10)
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

            v_lbl = QLabel("<b>N/A</b> <font color='#90A0B7'>(Loading...)</font>")
            v_lbl.setProperty("class", "card-value")
            cl.addWidget(v_lbl)
            self.xm_labels[key] = v_lbl

            cl.addWidget(QLabel(desc))
            r, c = divmod(idx, 3)
            grid_xm.addWidget(card, r, c)

        l_cross.addLayout(grid_xm)
        tabs.addTab(tab_cross, "CROSS-MARKET INDICATORS")

        # ── Tab 2: Macro Regime & Intermarket Dynamics ───────────────────────
        tab_regime = QWidget()
        l_regime = QVBoxLayout(tab_regime)

        grid_regime = QGridLayout()
        grid_regime.setSpacing(10)

        regime_cards = [
            ("MACRO REGIME STATE", "Current Regime", "regime_state"),
            ("GOLD / SILVER RATIO", "XAUUSD / XAGUSD", "gsr_value"),
            ("GSR 20D Z-SCORE", "Mean Reversion Deviation", "gsr_zscore"),
            ("2s10s CURVE SPREAD", "US10Y - US02Y Slope", "yield_slope"),
            ("GOLD-DXY 30D CORRELATION", "Rolling Return Coupling", "dxy_corr"),
            ("MACRO GATING STATUS", "Signal Veto Engine", "gating_status"),
        ]

        for idx, (title, desc, key) in enumerate(regime_cards):
            card = QFrame()
            card.setProperty("class", "card")
            cl = QVBoxLayout(card)
            cl.addWidget(QLabel(title))

            v_lbl = QLabel("<b>CALCULATING...</b>")
            v_lbl.setProperty("class", "card-value")
            cl.addWidget(v_lbl)
            self.regime_labels[key] = v_lbl

            cl.addWidget(QLabel(desc))
            r, c = divmod(idx, 3)
            grid_regime.addWidget(card, r, c)

        l_regime.addLayout(grid_regime)
        tabs.addTab(tab_regime, "MACRO REGIME DYNAMICS")

        # ── Tab 3: Macro Calendar & Releases ────────────────────────────────
        tab_macro = QWidget()
        l_macro = QVBoxLayout(tab_macro)

        t_macro = QTableWidget(6, 7)
        t_macro.setHorizontalHeaderLabels([
            "Release Time (UTC)", "Event Name", "Country", "Previous", "Forecast", "Actual", "Gold Impact"
        ])
        t_macro.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
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

        # Trigger initial fetch
        self._start_fetch()

    def _load_macro_regimes(self):
        try:
            store = DataStore()
            df = store.load_raw(symbol="XAUUSD", timeframe="H1")
            if df.empty:
                df, _ = generate_sample_data(timeframe="H1", days=60)

            df_macro = add_all_macro_features(df, use_synthetic_fallback=True)
            if not df_macro.empty:
                last = df_macro.iloc[-1]
                regime_code = int(last.get("macro_regime_code", 0))

                regime_names = {
                    MacroRegime.NEUTRAL: ("NEUTRAL / CONSOLIDATION", "#90A0B7"),
                    MacroRegime.DOLLAR_PRESSURE: ("DOLLAR PRESSURE (BEARISH)", "#FF5252"),
                    MacroRegime.INFLATION_HEDGE: ("INFLATION HEDGE (BULLISH)", "#00E676"),
                    MacroRegime.RISK_OFF_FLIGHT: ("RISK-OFF FLIGHT (BULLISH)", "#00E5FF"),
                }
                r_name, r_col = regime_names.get(regime_code, ("NEUTRAL", "#90A0B7"))
                self.regime_labels["regime_state"].setText(f"<font color='{r_col}'><b>{r_name}</b></font>")

                gsr = last.get("gold_silver_ratio", 85.0)
                self.regime_labels["gsr_value"].setText(f"<b>{gsr:.2f}</b>")

                gsr_z = last.get("gsr_zscore_20d", 0.0)
                z_col = "#FF5252" if gsr_z > 1.5 else ("#00E676" if gsr_z < -1.5 else "#90A0B7")
                self.regime_labels["gsr_zscore"].setText(f"<font color='{z_col}'><b>{gsr_z:+.2f} σ</b></font>")

                slope = last.get("yield_curve_slope", -0.25)
                self.regime_labels["yield_slope"].setText(f"<b>{slope:+.2f}%</b>")

                corr = last.get("gold_dxy_corr_30d", -0.72)
                self.regime_labels["dxy_corr"].setText(f"<b>{corr:+.2f}</b>")

                gating_txt = "BUY VETOED" if regime_code == MacroRegime.DOLLAR_PRESSURE else (
                    "SELL VETOED" if regime_code == MacroRegime.RISK_OFF_FLIGHT else "ACTIVE / BALANCED"
                )
                g_col = "#FF5252" if "VETOED" in gating_txt else "#00E676"
                self.regime_labels["gating_status"].setText(f"<font color='{g_col}'><b>{gating_txt}</b></font>")

        except Exception:
            pass

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

                color = "#90A0B7"
                if chg.startswith("+"):
                    color = "#00E676"
                elif chg.startswith("-"):
                    color = "#FF5252"

                self.xm_labels[key].setText(f"<b>{val}</b> <font color='{color}'>({chg})</font>")

        self._load_macro_regimes()

    def _on_fetch_error(self, err_msg):
        self.progress_bar.setVisible(False)
        self.btn_refresh.setEnabled(True)
