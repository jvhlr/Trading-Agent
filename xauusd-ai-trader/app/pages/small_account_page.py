"""
Small Account Mode ($200 Scenario) & Position Feasibility Calculator Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QDoubleSpinBox, QComboBox
)
from PySide6.QtCore import Qt


class SmallAccountPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── 1. Small Account Configuration Card ────────────────────────────
        cfg_card = QFrame()
        cfg_card.setProperty("class", "card")
        c_layout = QVBoxLayout(cfg_card)
        c_layout.addWidget(QLabel("SMALL ACCOUNT SCENARIO & RISK LIMITS"))

        grid = QGridLayout()

        grid.addWidget(QLabel("Account Balance ($):"), 0, 0)
        self.combo_bal = QComboBox()
        self.combo_bal.addItems(["$100.00", "$200.00 (Default)", "$500.00", "$1,000.00", "$5,000.00"])
        self.combo_bal.setCurrentText("$200.00 (Default)")
        self.combo_bal.currentTextChanged.connect(self._calculate_feasibility)
        grid.addWidget(self.combo_bal, 0, 1)

        grid.addWidget(QLabel("Max Risk Per Trade (%):"), 0, 2)
        self.spin_risk_pct = QDoubleSpinBox()
        self.spin_risk_pct.setRange(0.1, 5.0)
        self.spin_risk_pct.setValue(1.0)
        self.spin_risk_pct.setSuffix("%")
        self.spin_risk_pct.valueChanged.connect(self._calculate_feasibility)
        grid.addWidget(self.spin_risk_pct, 0, 3)

        grid.addWidget(QLabel("Stop Loss Distance ($/oz):"), 1, 0)
        self.spin_sl_dist = QDoubleSpinBox()
        self.spin_sl_dist.setRange(0.5, 50.0)
        self.spin_sl_dist.setValue(3.50)
        self.spin_sl_dist.setPrefix("$")
        self.spin_sl_dist.valueChanged.connect(self._calculate_feasibility)
        grid.addWidget(self.spin_sl_dist, 1, 1)

        grid.addWidget(QLabel("Broker Min Lot Size:"), 1, 2)
        self.lbl_min_lot = QLabel("<b>0.01 Lots</b> (1 oz)")
        grid.addWidget(self.lbl_min_lot, 1, 3)

        c_layout.addLayout(grid)
        layout.addWidget(cfg_card)

        # ── 2. Feasibility Result Banner ───────────────────────────────────
        self.res_card = QFrame()
        self.res_layout = QVBoxLayout(self.res_card)
        layout.addWidget(self.res_card)

        # Initial calculation
        self._calculate_feasibility()

    def _calculate_feasibility(self):
        # Clear old items
        for i in reversed(range(self.res_layout.count())):
            w = self.res_layout.itemAt(i).widget()
            if w:
                w.deleteLater()

        text_bal = self.combo_bal.currentText().split()[0].replace("$", "").replace(",", "")
        balance = float(text_bal)
        risk_pct = self.spin_risk_pct.value()
        sl_dist = self.spin_sl_dist.value()

        max_risk_dollars = balance * (risk_pct / 100.0)

        # Position size in lots (1 lot = 100 oz in standard XAUUSD, 0.01 lot = 1 oz)
        # Risk per 0.01 lot = sl_dist * 1.0 = sl_dist
        calc_lots = max_risk_dollars / (sl_dist * 100.0)
        min_broker_lots = 0.01
        min_risk_dollars = min_broker_lots * 100.0 * sl_dist

        is_feasible = calc_lots >= min_broker_lots

        if is_feasible:
            self.res_card.setStyleSheet("background-color: #1B2D24; border: 2px solid #00E676; border-radius: 6px; padding: 16px;")
            color = "#00E676"
            verdict = "FEASIBLE — TRADE CLEARED BY RISK ENGINE"
            subtext = f"Calculated Lot Size: <b>{calc_lots:.3f} lots</b> | Maximum Risk: <b>${max_risk_dollars:.2f}</b>"
        else:
            self.res_card.setStyleSheet("background-color: #2E2818; border: 2px solid #FFAB00; border-radius: 6px; padding: 16px;")
            color = "#FFAB00"
            verdict = "NOT FEASIBLE — DECISION FORCED TO WAIT"
            subtext = (
                f"Permitted Account Risk ({risk_pct}%): <b>${max_risk_dollars:.2f}</b><br>"
                f"Minimum Broker Trade (0.01 lot @ ${sl_dist:.2f} SL): <b>${min_risk_dollars:.2f}</b><br><br>"
                f"<b>REASON:</b> Minimum tradable position (0.01 lots) exceeds maximum permitted account risk limit (${max_risk_dollars:.2f})."
            )

        lbl_v = QLabel(f"POSITION FEASIBILITY VERDICT: <b>{verdict}</b>")
        lbl_v.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {color};")

        lbl_s = QLabel(subtext)
        lbl_s.setStyleSheet("font-size: 13px; color: #E0E6ED;")

        self.res_layout.addWidget(lbl_v)
        self.res_layout.addWidget(lbl_s)
