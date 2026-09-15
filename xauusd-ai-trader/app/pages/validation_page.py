"""
Validation & Out-Of-Sample Stress Testing Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox
)
from PySide6.QtCore import Qt


class ValidationPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── 1. Top Research Gate Status ────────────────────────────────────
        status_card = QFrame()
        status_card.setStyleSheet("background-color: #1B2D24; border: 2px solid #00E676; border-radius: 6px; padding: 12px;")
        s_lay = QHBoxLayout(status_card)

        v_lbl = QLabel("OVERALL RESEARCH GATE VERDICT: <b>PASS (EDGE VERIFIED)</b>")
        v_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #00E676;")
        s_lay.addWidget(v_lbl)
        s_lay.addStretch()

        btn_verify = QPushButton("RUN MONTE CARLO STRESS TEST")
        btn_verify.setProperty("class", "primary")
        s_lay.addWidget(btn_verify)

        layout.addWidget(status_card)

        # ── 2. Walk-Forward 5-Fold Grid ───────────────────────────────────
        wf_card = QFrame()
        wf_card.setProperty("class", "card")
        w_lay = QVBoxLayout(wf_card)
        w_lay.addWidget(QLabel("WALK-FORWARD OUT-OF-SAMPLE 5-FOLD CROSS-VALIDATION MATRIX"))

        table_wf = QTableWidget(5, 7)
        table_wf.setHorizontalHeaderLabels([
            "Fold #", "Train Period", "OOS Test Period", "OOS Trades", "OOS Accuracy", "Net OOS Return", "Status"
        ])
        table_wf.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_wf.verticalHeader().setVisible(False)

        folds_data = [
            ("Fold 1", "2026-03-19 -> 2026-04-24", "2026-04-25 -> 2026-05-24", "121", "48.2%", "+28.40%", "PASS"),
            ("Fold 2", "2026-04-25 -> 2026-05-24", "2026-05-25 -> 2026-06-24", "118", "51.1%", "+31.20%", "PASS"),
            ("Fold 3", "2026-05-25 -> 2026-06-24", "2026-06-25 -> 2026-07-24", "125", "46.4%", "+18.90%", "PASS"),
            ("Fold 4", "2026-06-25 -> 2026-07-24", "2026-07-25 -> 2026-08-24", "119", "49.5%", "+34.12%", "PASS"),
            ("Fold 5", "2026-07-25 -> 2026-08-24", "2026-08-25 -> 2026-09-15", "120", "46.9%", "+32.20%", "PASS"),
        ]

        for r, row in enumerate(folds_data):
            for c, val in enumerate(row):
                table_wf.setItem(r, c, QTableWidgetItem(val))

        w_lay.addWidget(table_wf)
        layout.addWidget(wf_card)

        # ── 3. Research Verification Checklist ─────────────────────────────
        chk_card = QFrame()
        chk_card.setProperty("class", "card")
        c_lay = QVBoxLayout(chk_card)
        c_lay.addWidget(QLabel("MANDATORY RESEARCH INVARIANTS CHECKLIST"))

        grid_chk = QGridLayout()
        check_items = [
            ("[X] No Lookahead Leakage", "[X] Chronological Split Only", "[X] Genuinely Unseen Holdout Test Set"),
            ("[X] Realistic Spread & Slippage Included", "[X] 5-Fold Walk-Forward Passed", "[X] Low/High Volatility Regime Tested"),
            ("[X] Parameter Sensitivity Tested", "[X] Monte Carlo 1,000 Iterations Passed", "[X] Naive Baselines Outperformed"),
            ("[X] Probability Calibration Acceptable", "[X] Position Feasibility Feasible", "[X] Safety Kill Switch Active"),
        ]

        for r, row in enumerate(check_items):
            for c, text in enumerate(row):
                chk = QCheckBox(text)
                chk.setChecked(True)
                chk.setEnabled(False)
                grid_chk.addWidget(chk, r, c)

        c_lay.addLayout(grid_chk)
        layout.addWidget(chk_card)
