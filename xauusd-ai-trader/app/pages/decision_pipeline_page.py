"""
Transparent Decision Pipeline Stage Inspector Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea
)


class DecisionPipelinePage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll_content = QWidget()
        s_layout = QVBoxLayout(scroll_content)

        stages = [
            ("1. MARKET DATA INGESTION", "PASS", "MT5 (XAUUSD H1)", "2,794 candles UTC, median spread: 4 pts ($0.40/oz)"),
            ("2. FEATURE ENGINEERING", "PASS", "35 Deterministic Features", "Price returns, Technical indicators (SMA/RSI/MACD/BB), Structure swing levels"),
            ("3. ML MODEL PREDICTION", "PASS", "Momentum Classifier v1.0", "Prob UP: 51.7% | Prob DOWN: 46.0% | Prob FLAT: 2.3% | Exp Return: +0.14%"),
            ("4. CROSS-MARKET & MACRO", "WARN", "CPI Release Impending", "DXY: 104.12 (+0.18%) | US 10Y: 4.21% | CPI release in 45 mins"),
            ("5. HISTORICAL MEMORY", "PASS", "94.2% K-NN Match", "Analogue 2024-04-12 (+1.42% forward return, MFE +$38.50)"),
            ("6. DECISION ENGINE", "PASS (WAIT)", "Rule Evaluation", "Signal: BUY, but expected return (+0.14%) below required threshold (+0.25%)"),
            ("7. RISK ENGINE", "BLOCKED", "Deterministic Risk Check", "Risk limit ($2.00) vs Broker Min Lot (0.01 lot = $3.50 risk). Feasibility: NO"),
            ("8. EXECUTION CHECK", "DISABLED", "Safety Kill Switch", "Trading Mode: RESEARCH ONLY. Order placement locked."),
        ]

        for title, status, desc, detail in stages:
            card = QFrame()
            card.setProperty("class", "card")
            cl = QVBoxLayout(card)

            hdr = QHBoxLayout()
            lbl_title = QLabel(f"<b>{title}</b>")
            lbl_title.setStyleSheet("font-size: 14px;")
            hdr.addWidget(lbl_title)

            color = "#00E676" if "PASS" in status else ("#FFAB00" if "WARN" in status or "WAIT" in status else "#FF5252")
            lbl_status = QLabel(f"<b>{status}</b>")
            lbl_status.setStyleSheet(f"color: {color}; font-weight: 700;")
            hdr.addWidget(lbl_status)
            cl.addLayout(hdr)

            cl.addWidget(QLabel(f"<b>Output:</b> {desc}"))
            cl.addWidget(QLabel(f"<b>Details:</b> {detail}"))

            s_layout.addWidget(card)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
