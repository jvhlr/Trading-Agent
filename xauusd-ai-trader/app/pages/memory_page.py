"""
Historical Memory & Regime Similarity Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView
)


class MemoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── 1. Disclaimer Banner ───────────────────────────────────────────
        warn_card = QFrame()
        warn_card.setStyleSheet("background-color: #2E2818; border: 2px solid #FFAB00; border-radius: 6px; padding: 12px;")
        w_lay = QHBoxLayout(warn_card)
        lbl_w = QLabel("⚠️ <b>HISTORICAL SIMILARITY IS EVIDENCE, NOT PROOF.</b> Past market analogues do not guarantee future performance.")
        lbl_w.setStyleSheet("color: #FFAB00; font-size: 13px;")
        w_lay.addWidget(lbl_w)
        layout.addWidget(warn_card)

        # ── 2. Top Matches Table ───────────────────────────────────────────
        table_card = QFrame()
        table_card.setProperty("class", "card")
        t_lay = QVBoxLayout(table_card)
        t_lay.addWidget(QLabel("NEAREST NEIGHBOR HISTORICAL MARKET ANALOGUES (K-NN REPLACEMENT)"))

        table_mem = QTableWidget(5, 7)
        table_mem.setHorizontalHeaderLabels([
            "Similarity Score", "Historical Date", "Market Regime", "Macro Context", "Forward 24h Return", "MFE ($)", "MAE ($)"
        ])
        table_mem.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_mem.verticalHeader().setVisible(False)

        mem_data = [
            ("94.2%", "2024-04-12 14:00 UTC", "Low-Vol Trending", "Pre-CPI Consolidation", "+1.42%", "+$38.50", "-$6.20"),
            ("91.8%", "2023-11-08 09:00 UTC", "Low-Vol Trending", "DXY Resistance Test", "+0.95%", "+$24.10", "-$4.80"),
            ("88.5%", "2025-01-15 16:00 UTC", "Low-Vol Range", "Post-FOMC Digest", "-0.32%", "+$11.00", "-$14.30"),
            ("86.1%", "2022-08-04 11:00 UTC", "High-Vol Breakout", "NFP Release Week", "+2.10%", "+$52.00", "-$9.10"),
            ("84.7%", "2026-02-18 10:00 UTC", "Low-Vol Trending", "US Yield Drop", "+0.88%", "+$21.40", "-$3.90"),
        ]

        for r, row in enumerate(mem_data):
            for c, val in enumerate(row):
                table_mem.setItem(r, c, QTableWidgetItem(val))

        t_lay.addWidget(table_mem)
        layout.addWidget(table_card)
