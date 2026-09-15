"""
Paper Trading Terminal Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView
)


class PaperTradingPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── 1. Controls & Portfolio Summary ────────────────────────────────
        ctrl_card = QFrame()
        ctrl_card.setProperty("class", "card")
        c_lay = QHBoxLayout(ctrl_card)

        c_lay.addWidget(QLabel("<b>PAPER TRADING STATE:</b> <font color='#FFAB00'>IDLE (SIMULATION READY)</font>"))
        c_lay.addStretch()

        btn_start = QPushButton("START PAPER TRADING")
        btn_start.setProperty("class", "primary")
        c_lay.addWidget(btn_start)

        btn_stop = QPushButton("STOP PAPER TRADING")
        c_lay.addWidget(btn_stop)

        layout.addWidget(ctrl_card)

        # ── 2. Paper Portfolio Cards ───────────────────────────────────────
        p_grid = QGridLayout()
        p_cards = [
            ("VIRTUAL BALANCE", "$10,000.00", "Starting Equity: $10,000.00", "card-value"),
            ("VIRTUAL NET P&L", "+$420.50", "+4.21% Return", "card-value pill-enabled"),
            ("PAPER WIN RATE", "52.4%", "21 Total Paper Trades", "card-value pill-info"),
            ("MAX PAPER DRAWDOWN", "-1.85%", "Within Risk Limit", "card-value pill-info"),
        ]
        for idx, (title, val, sub, style_cls) in enumerate(p_cards):
            card = QFrame()
            card.setProperty("class", "card")
            cl = QVBoxLayout(card)
            cl.addWidget(QLabel(title))
            v_lbl = QLabel(val)
            v_lbl.setProperty("class", style_cls)
            cl.addWidget(v_lbl)
            cl.addWidget(QLabel(sub))
            p_grid.addWidget(card, 0, idx)

        layout.addLayout(p_grid)

        # ── 3. Virtual Trades Table ───────────────────────────────────────
        pt_card = QFrame()
        pt_card.setProperty("class", "card")
        pt_lay = QVBoxLayout(pt_card)
        pt_lay.addWidget(QLabel("PAPER TRADING EXECUTION & CANDIDATE LOG"))

        table_pt = QTableWidget(5, 8)
        table_pt.setHorizontalHeaderLabels([
            "Timestamp", "Signal", "Model Conf", "Entry Price", "SL", "TP", "Position Size", "Paper P&L ($)"
        ])
        table_pt.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_pt.verticalHeader().setVisible(False)

        paper_trades = [
            ("2026-09-15 11:00", "BUY", "54.2%", "$4,288.50", "$4,275.00", "$4,310.00", "0.07 Lots", "+$150.50"),
            ("2026-09-14 15:00", "WAIT", "51.0%", "N/A", "N/A", "N/A", "0.00 Lots", "$0.00 (Edge Below Thresh)"),
            ("2026-09-13 09:00", "SELL", "58.1%", "$4,302.10", "$4,315.00", "$4,275.00", "0.07 Lots", "+$189.70"),
            ("2026-09-11 16:00", "BUY", "53.5%", "$4,290.00", "$4,278.00", "$4,310.00", "0.07 Lots", "-$84.00"),
            ("2026-09-10 10:00", "BUY", "56.0%", "$4,270.00", "$4,258.00", "$4,295.00", "0.07 Lots", "+$164.30"),
        ]

        for r, row in enumerate(paper_trades):
            for c, val in enumerate(row):
                table_pt.setItem(r, c, QTableWidgetItem(val))

        pt_lay.addWidget(table_pt)
        layout.addWidget(pt_card)
