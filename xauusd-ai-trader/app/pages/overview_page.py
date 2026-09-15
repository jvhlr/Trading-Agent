"""
Overview / Executive Control Dashboard Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QScrollArea, QProgressBar
)
from PySide6.QtCore import Qt


class OverviewPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

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

        cards_data = [
            ("SYSTEM STATUS", "OPERATIONAL", "MetaTrader 5 & SQLite active", "pill-enabled"),
            ("DATA STATUS", "VALID", "2,794 candles (H1 MT5)", "pill-info"),
            ("MODEL STATUS", "MOMENTUM v1.0", "OOS Accuracy: 51.7%", "pill-gold"),
            ("MARKET STATE", "XAUUSD $4,294.74", "Spread: 4 pts ($0.40/oz)", "pill-info"),
            ("RISK STATUS", "SAFE (LOCKED)", "Max Loss: 3.0% / Daily: $0.00", "pill-enabled"),
            ("TRADING MODE", "RESEARCH ONLY", "Live Execution: DISABLED", "pill-disabled"),
        ]

        for idx, (title, value, subtext, style_cls) in enumerate(cards_data):
            card = QFrame()
            card.setProperty("class", "card")
            card_layout = QVBoxLayout(card)

            lbl_title = QLabel(title)
            lbl_title.setProperty("class", "card-title")

            lbl_val = QLabel(value)
            lbl_val.setProperty("class", f"card-value {style_cls}")

            lbl_sub = QLabel(subtext)
            lbl_sub.setProperty("class", "card-subtext")

            card_layout.addWidget(lbl_title)
            card_layout.addWidget(lbl_val)
            card_layout.addWidget(lbl_sub)

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
        m_items = [
            ("Spot Price:", "$4,294.74", "ATR (14):", "$16.75"),
            ("Bid / Ask:", "4294.54 / 4294.94", "Volatility:", "1.42% (Normal)"),
            ("Spread:", "4 pts ($0.40/oz)", "Trend (H1):", "BULLISH (SMA 20>50)"),
            ("Regime:", "Low-Vol Trending", "Session:", "London / NY Overlap"),
            ("DXY Index:", "104.12 (+0.18%)", "US 10Y Yield:", "4.21% (-2 bps)"),
            ("VIX Index:", "14.85 (Calm)", "Silver (XAGUSD):", "$31.40 (+0.8%)"),
        ]
        for r, (k1, v1, k2, v2) in enumerate(m_items):
            m_grid.addWidget(QLabel(k1), r, 0)
            m_grid.addWidget(QLabel(f"<b>{v1}</b>"), r, 1)
            m_grid.addWidget(QLabel(k2), r, 2)
            m_grid.addWidget(QLabel(f"<b>{v2}</b>"), r, 3)

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
        mod_grid.addWidget(QLabel("Probability UP:"), 0, 0)
        mod_grid.addWidget(QLabel("<font color='#00E676'><b>51.7%</b></font>"), 0, 1)
        mod_grid.addWidget(QLabel("Probability DOWN:"), 1, 0)
        mod_grid.addWidget(QLabel("<font color='#FF5252'><b>46.0%</b></font>"), 1, 1)
        mod_grid.addWidget(QLabel("Probability FLAT:"), 2, 0)
        mod_grid.addWidget(QLabel("<font color='#FFAB00'><b>2.3%</b></font>"), 2, 1)

        mod_grid.addWidget(QLabel("Expected Return:"), 3, 0)
        mod_grid.addWidget(QLabel("<b>+0.14%</b>"), 3, 1)
        mod_grid.addWidget(QLabel("Expected Volatility:"), 4, 0)
        mod_grid.addWidget(QLabel("<b>0.38%</b>"), 4, 1)
        mod_grid.addWidget(QLabel("Calibration Score:"), 5, 0)
        mod_grid.addWidget(QLabel("<font color='#00E5FF'><b>ACCEPTABLE (Brier: 0.52)</b></font>"), 5, 1)

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
        dec_box_layout = QVBoxLayout(dec_box)
        lbl_dec = QLabel("WAIT")
        lbl_dec.setStyleSheet("font-size: 32px; font-weight: 800; color: #FFAB00;")
        lbl_dec_sub = QLabel("Action: No position authorized")
        lbl_dec_sub.setStyleSheet("color: #C5D1E0; font-size: 12px;")
        dec_box_layout.addWidget(lbl_dec, alignment=Qt.AlignCenter)
        dec_box_layout.addWidget(lbl_dec_sub, alignment=Qt.AlignCenter)

        d_row.addWidget(dec_box, stretch=1)

        # Reasons Panel
        reasons_box = QVBoxLayout()
        lbl_reasons_header = QLabel("<b>WHY SYSTEM CHOSE WAIT:</b>")
        lbl_reasons_header.setStyleSheet("color: #FFAB00;")
        reasons_box.addWidget(lbl_reasons_header)

        reasons = [
            "• Expected directional edge (+0.14%) is below minimum threshold (+0.25%).",
            "• Spread ($0.40/oz) consumes 35% of target expected movement.",
            "• High-impact US CPI news release scheduled in 45 minutes.",
            "• System invariant: Live trading remains locked by safety kill switch.",
        ]
        for r in reasons:
            reasons_box.addWidget(QLabel(r))

        d_row.addLayout(reasons_box, stretch=3)
        d_layout.addLayout(d_row)

        layout.addWidget(decision_card)

        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
