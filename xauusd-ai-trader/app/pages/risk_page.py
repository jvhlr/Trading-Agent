"""
Deterministic Risk Engine Dashboard Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)


class RiskPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── 1. Emergency Kill Switch Card ─────────────────────────────────
        kill_card = QFrame()
        kill_card.setStyleSheet("background-color: #2D1B22; border: 2px solid #FF5252; border-radius: 6px; padding: 14px;")
        k_lay = QHBoxLayout(kill_card)

        lbl_k = QLabel("🚨 <b>SYSTEM RISK ENGINE: SAFE / LOCKED</b> (Live Order Placement Disallowed)")
        lbl_k.setStyleSheet("color: #FF5252; font-size: 14px; font-weight: 700;")
        k_lay.addWidget(lbl_k)
        k_lay.addStretch()

        self.btn_kill = QPushButton("ENGAGE EMERGENCY KILL SWITCH")
        self.btn_kill.setProperty("class", "danger")
        k_lay.addWidget(self.btn_kill)

        layout.addWidget(kill_card)

        # ── 2. Risk Metrics Grid ──────────────────────────────────────────
        r_grid = QGridLayout()
        r_grid.setSpacing(12)

        metrics = [
            ("ACCOUNT EQUITY", "$10,000.00", "Starting Balance: $10,000.00", "pill-enabled"),
            ("MAX RISK PER TRADE", "1.0% ($100.00)", "Fixed Risk Budgeting", "pill-info"),
            ("MAX DAILY LOSS LIMIT", "3.0% ($300.00)", "Current Daily Realized Loss: $0.00", "pill-enabled"),
            ("MAX DRAWDOWN LIMIT", "10.0% ($1,000.00)", "Peak Equity: $10,000.00", "pill-enabled"),
            ("MAX POSITIONS", "1 Position", "Current Open Exposure: 0 Lots", "pill-info"),
            ("MAX SPREAD THRESHOLD", "$0.80 / oz", "Current Market Spread: $0.40 / oz", "pill-enabled"),
        ]

        for idx, (title, val, sub, style_cls) in enumerate(metrics):
            card = QFrame()
            card.setProperty("class", "card")
            cl = QVBoxLayout(card)
            cl.addWidget(QLabel(title))
            v_lbl = QLabel(val)
            v_lbl.setProperty("class", f"card-value {style_cls}")
            cl.addWidget(v_lbl)
            cl.addWidget(QLabel(sub))
            r, c = divmod(idx, 3)
            r_grid.addWidget(card, r, c)

        layout.addLayout(r_grid)

        # ── 3. Risk Rejection Audit Log ────────────────────────────────────
        log_card = QFrame()
        log_card.setProperty("class", "card")
        l_lay = QVBoxLayout(log_card)
        l_lay.addWidget(QLabel("DETERMINISTIC RISK REJECTION AUDIT LOG"))

        table_risk = QTableWidget(4, 5)
        table_risk.setHorizontalHeaderLabels([
            "Timestamp (UTC)", "Proposed Action", "Proposed Lot Size", "Rejection Reason", "Engine Status"
        ])
        table_risk.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_risk.verticalHeader().setVisible(False)

        rejections = [
            ("2026-09-15 14:30:00", "BUY XAUUSD", "0.01 Lots", "Position risk ($3.50) exceeds permitted $200 account risk ($2.00)", "REJECTED (SAFE)"),
            ("2026-09-14 18:15:00", "SELL XAUUSD", "0.05 Lots", "Spread ($1.20/oz) exceeds max allowed spread threshold ($0.80/oz)", "REJECTED (SAFE)"),
            ("2026-09-12 12:00:00", "BUY XAUUSD", "0.02 Lots", "High-impact NFP news release in 15 minutes", "REJECTED (SAFE)"),
            ("2026-09-10 09:45:00", "BUY XAUUSD", "0.01 Lots", "System invariant: Live trading mode DISABLED", "REJECTED (SAFE)"),
        ]

        for r, row in enumerate(rejections):
            for c, val in enumerate(row):
                table_risk.setItem(r, c, QTableWidgetItem(val))

        l_lay.addWidget(table_risk)
        layout.addWidget(log_card)
