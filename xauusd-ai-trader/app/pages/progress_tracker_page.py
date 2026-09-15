"""
Research Progression Phase Tracker Page (Phase 0 -> Phase 11).
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView
)


class ProgressTrackerPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        card = QFrame()
        card.setProperty("class", "card")
        c_lay = QVBoxLayout(card)

        c_lay.addWidget(QLabel("XAUUSD AI TRADING SYSTEM — MASTER PROGRESSION ROADMAP"))

        table_prog = QTableWidget(12, 4)
        table_prog.setHorizontalHeaderLabels([
            "Phase #", "Milestone Name", "Prerequisites", "Status"
        ])
        table_prog.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_prog.verticalHeader().setVisible(False)

        phases = [
            ("Phase 0", "Research Definition", "None", "PASSED"),
            ("Phase 1", "Data Foundation (MT5 / SQLite)", "Phase 0", "PASSED"),
            ("Phase 2", "Baseline Quantitative ML", "Phase 1", "PASSED"),
            ("Phase 3", "Realistic Research Backtester & Walk-Forward", "Phase 2", "PASSED (Gate #1 Clearance)"),
            ("Phase 4", "Cross-Market & Macro Integration", "Phase 3", "IN PROGRESS"),
            ("Phase 5", "News / Event Intelligence", "Phase 4", "NOT STARTED"),
            ("Phase 6", "Historical Market Memory (K-NN)", "Phase 5", "IN PROGRESS"),
            ("Phase 7", "Market-State Fusion Engine", "Phase 6", "NOT STARTED"),
            ("Phase 8", "LLM Evaluation (Ablation Testing)", "Phase 7", "NOT STARTED"),
            ("Phase 9", "Paper Trading Simulation", "Phase 8", "IN PROGRESS"),
            ("Phase 10", "Execution Infrastructure & Reconciliation", "Phase 9", "NOT STARTED"),
            ("Phase 11", "Small Account Live Deployment ($200)", "Phase 10 + Explicit Auth", "LOCKED (SAFETY GATE)"),
        ]

        for r, (ph, name, pre, st) in enumerate(phases):
            table_prog.setItem(r, 0, QTableWidgetItem(ph))
            table_prog.setItem(r, 1, QTableWidgetItem(name))
            table_prog.setItem(r, 2, QTableWidgetItem(pre))
            table_prog.setItem(r, 3, QTableWidgetItem(st))

        c_lay.addWidget(table_prog)
        layout.addWidget(card)
