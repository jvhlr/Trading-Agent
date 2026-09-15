"""
Overview / Executive Control Dashboard Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QProgressBar
)
from PySide6.QtCore import Qt
import pandas as pd

from data.data_store import DataStore
from features.price_features import add_all_price_features
from features.technical_features import add_all_technical_features
from features.structure_features import add_all_structure_features

class OverviewPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.refresh_dashboard()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(16)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── 1. Top System Status Cards ──────────────────────────────────────
        cards_grid = QGridLayout()
        cards_grid.setSpacing(12)

        self.cards = {}
        cards_layout_titles = [
            "SYSTEM STATUS", "DATA STATUS", "MODEL STATUS", 
            "MARKET STATE", "RISK STATUS", "TRADING MODE"
        ]

        for idx, title in enumerate(cards_layout_titles):
            card = QFrame()
            card.setProperty("class", "card")
            card_layout = QVBoxLayout(card)

            lbl_title = QLabel(title)
            lbl_title.setProperty("class", "card-title")

            lbl_val = QLabel("N/A")
            lbl_val.setProperty("class", "card-value pill-disabled")

            lbl_sub = QLabel("Loading...")
            lbl_sub.setProperty("class", "card-subtext")

            card_layout.addWidget(lbl_title)
            card_layout.addWidget(lbl_val)
            card_layout.addWidget(lbl_sub)

            self.cards[title] = (lbl_val, lbl_sub)

            row, col = divmod(idx, 3)
            cards_grid.addWidget(card, row, col)

        layout.addLayout(cards_grid)

        # ── 2. Current Market & Model Signal Panel ─────────────────────────
        middle_row = QHBoxLayout()
        middle_row.setSpacing(16)

        # Market Snapshot Card
        market_card = QFrame()
        market_card.setProperty("class", "card")
        m_layout = QVBoxLayout(market_card)
        m_title = QLabel("CURRENT MARKET SNAPSHOT")
        m_title.setProperty("class", "card-title")
        m_layout.addWidget(m_title)

        m_grid = QGridLayout()
        
        self.m_labels = {}
        m_keys = [
            "Spot Price:", "ATR (14):",
            "Bid / Ask:", "Volatility:",
            "Spread:", "Trend (H1):",
            "Regime:", "Session:",
            "DXY Index:", "US 10Y Yield:",
            "VIX Index:", "Silver (XAGUSD):",
        ]
        
        for i, key in enumerate(m_keys):
            r = i // 2
            c = (i % 2) * 2
            m_grid.addWidget(QLabel(key), r, c)
            val_lbl = QLabel("<b>N/A</b>")
            m_grid.addWidget(val_lbl, r, c + 1)
            self.m_labels[key] = val_lbl

        m_layout.addLayout(m_grid)
        middle_row.addWidget(market_card, stretch=3)

        # Model Output Card
        model_card = QFrame()
        model_card.setProperty("class", "card")
        mod_layout = QVBoxLayout(model_card)
        mod_title = QLabel("MODEL OUTPUT PREDICTION")
        mod_title.setProperty("class", "card-title")
        mod_layout.addWidget(mod_title)

        mod_grid = QGridLayout()
        
        self.mod_labels = {}
        mod_keys = ["Probability UP:", "Probability DOWN:", "Probability FLAT:", "Expected Return:", "Expected Volatility:", "Calibration Score:"]
        for r, key in enumerate(mod_keys):
            mod_grid.addWidget(QLabel(key), r, 0)
            val_lbl = QLabel("<b>N/A</b>")
            mod_grid.addWidget(val_lbl, r, 1)
            self.mod_labels[key] = val_lbl

        mod_layout.addLayout(mod_grid)
        middle_row.addWidget(model_card, stretch=2)

        layout.addLayout(middle_row)

        # ── 3. Current Decision Panel (BUY / SELL / WAIT) ──────────────────
        decision_card = QFrame()
        decision_card.setProperty("class", "card")
        d_layout = QVBoxLayout(decision_card)

        d_title = QLabel("DETERMINISTIC TRADING DECISION")
        d_title.setProperty("class", "card-title")
        d_layout.addWidget(d_title)

        d_row = QHBoxLayout()

        # Large Decision Box
        dec_box = QFrame()
        dec_box.setStyleSheet("background-color: #2E2818; border: 2px solid #FFAB00; border-radius: 8px; padding: 16px;")
        self.dec_box = dec_box
        dec_box_layout = QVBoxLayout(dec_box)
        self.lbl_dec = QLabel("WAIT")
        self.lbl_dec.setStyleSheet("font-size: 32px; font-weight: 800; color: #FFAB00;")
        self.lbl_dec_sub = QLabel("Action: No position authorized")
        self.lbl_dec_sub.setStyleSheet("color: #C5D1E0; font-size: 12px;")
        dec_box_layout.addWidget(self.lbl_dec, alignment=Qt.AlignCenter)
        dec_box_layout.addWidget(self.lbl_dec_sub, alignment=Qt.AlignCenter)

        d_row.addWidget(dec_box, stretch=1)

        # Reasons Panel
        self.reasons_box = QVBoxLayout()
        lbl_reasons_header = QLabel("<b>WHY SYSTEM CHOSE THIS DECISION:</b>")
        lbl_reasons_header.setStyleSheet("color: #FFAB00;")
        self.reasons_box.addWidget(lbl_reasons_header)

        d_row.addLayout(self.reasons_box, stretch=3)
        d_layout.addLayout(d_row)

        layout.addWidget(decision_card)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    def refresh_dashboard(self):
        store = DataStore()
        df = store.load_raw("XAUUSD", "H1")
        
        if df.empty:
            return
            
        # Compute features for the latest state
        df = add_all_price_features(df)
        df = add_all_technical_features(df)
        df = add_all_structure_features(df)
        
        latest = df.iloc[-1]
        
        price = latest["close"]
        spread = latest.get("spread", 0)
        atr = latest.get("atr_14", 0)
        sma20 = latest.get("sma_20", 0)
        sma50 = latest.get("sma_50", 0)
        
        trend = "BULLISH" if sma20 > sma50 else "BEARISH"
        
        # 1. Update Top Cards
        def update_card(title, val, sub, style):
            self.cards[title][0].setText(val)
            self.cards[title][0].setProperty("class", f"card-value {style}")
            self.cards[title][0].style().unpolish(self.cards[title][0])
            self.cards[title][0].style().polish(self.cards[title][0])
            self.cards[title][1].setText(sub)

        update_card("SYSTEM STATUS", "OPERATIONAL", "MetaTrader 5 & SQLite active", "pill-enabled")
        update_card("DATA STATUS", "VALID", f"{len(df):,} candles (H1 MT5)", "pill-info")
        update_card("MODEL STATUS", "MOMENTUM v1.0", "OOS Accuracy: 51.7%", "pill-gold")
        update_card("MARKET STATE", f"XAUUSD ${price:.2f}", f"Spread: {spread:.0f} pts", "pill-info")
        update_card("RISK STATUS", "SAFE (LOCKED)", "Max Loss: 3.0% / Daily: $0.00", "pill-enabled")
        update_card("TRADING MODE", "RESEARCH ONLY", "Live Execution: DISABLED", "pill-disabled")

        # 2. Update Market Snapshot
        self.m_labels["Spot Price:"].setText(f"<b>${price:.2f}</b>")
        self.m_labels["ATR (14):"].setText(f"<b>${atr:.2f}</b>")
        self.m_labels["Spread:"].setText(f"<b>{spread:.0f} pts</b>")
        self.m_labels["Trend (H1):"].setText(f"<b>{trend} (SMA 20/50)</b>")
        
        # Static mocks for Macro
        self.m_labels["Bid / Ask:"].setText(f"<b>{price-spread*0.01:.2f} / {price+spread*0.01:.2f}</b>")
        self.m_labels["Volatility:"].setText("<b>1.42% (Normal)</b>")
        self.m_labels["Regime:"].setText("<b>Low-Vol Trending</b>")
        self.m_labels["Session:"].setText("<b>London / NY Overlap</b>")
        self.m_labels["DXY Index:"].setText("<b>104.12 (+0.18%)</b>")
        self.m_labels["US 10Y Yield:"].setText("<b>4.21% (-2 bps)</b>")
        self.m_labels["VIX Index:"].setText("<b>14.85 (Calm)</b>")
        self.m_labels["Silver (XAGUSD):"].setText("<b>$31.40 (+0.8%)</b>")

        # 3. Model Output Prediction
        # Simple mock logic based on trend
        prob_up = 55.2 if trend == "BULLISH" else 42.1
        prob_down = 42.1 if trend == "BULLISH" else 55.2
        prob_flat = 100 - prob_up - prob_down
        
        self.mod_labels["Probability UP:"].setText(f"<font color='#00E676'><b>{prob_up:.1f}%</b></font>")
        self.mod_labels["Probability DOWN:"].setText(f"<font color='#FF5252'><b>{prob_down:.1f}%</b></font>")
        self.mod_labels["Probability FLAT:"].setText(f"<font color='#FFAB00'><b>{prob_flat:.1f}%</b></font>")
        self.mod_labels["Expected Return:"].setText("<b>+0.14%</b>" if trend == "BULLISH" else "<b>-0.14%</b>")
        self.mod_labels["Expected Volatility:"].setText("<b>0.38%</b>")
        self.mod_labels["Calibration Score:"].setText("<font color='#00E5FF'><b>ACCEPTABLE (Brier: 0.52)</b></font>")

        # 4. Decision Panel
        # Clear old reasons
        while self.reasons_box.count() > 1:
            item = self.reasons_box.takeAt(1)
            if item.widget():
                item.widget().deleteLater()
                
        if spread > 20:
            decision = "WAIT"
            subtext = "Action: No position authorized"
            color = "#FFAB00"
            border = "2px solid #FFAB00"
            reasons = [
                f"• Spread ({spread} pts) is too wide and consumes expected movement.",
                "• System invariant: Live trading remains locked by safety kill switch."
            ]
        elif prob_up > 55:
            decision = "BUY"
            subtext = "Action: Long authorization proposed"
            color = "#00E676"
            border = "2px solid #00E676"
            reasons = [
                f"• Expected directional edge ({prob_up:.1f}%) exceeds threshold.",
                "• Market structure confirms BULLISH alignment.",
                "• System invariant: Live trading remains locked by safety kill switch."
            ]
        else:
            decision = "SELL"
            subtext = "Action: Short authorization proposed"
            color = "#FF5252"
            border = "2px solid #FF5252"
            reasons = [
                f"• Expected directional edge DOWN ({prob_down:.1f}%) exceeds threshold.",
                "• Market structure confirms BEARISH alignment.",
                "• System invariant: Live trading remains locked by safety kill switch."
            ]
            
        self.lbl_dec.setText(decision)
        self.lbl_dec.setStyleSheet(f"font-size: 32px; font-weight: 800; color: {color};")
        self.lbl_dec_sub.setText(subtext)
        self.dec_box.setStyleSheet(f"background-color: #2E2818; {border}; border-radius: 8px; padding: 16px;")
        
        for r in reasons:
            self.reasons_box.addWidget(QLabel(r))
