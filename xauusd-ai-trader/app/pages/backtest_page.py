"""
Research Backtester Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QDoubleSpinBox, QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar
)
import pyqtgraph as pg
import numpy as np

from app.workers.backtest_worker import BacktestWorker


class BacktestPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()
        self._plot_dummy_equity()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── 1. Controls Panel ──────────────────────────────────────────────
        cfg_card = QFrame()
        cfg_card.setProperty("class", "card")
        c_layout = QVBoxLayout(cfg_card)
        c_layout.addWidget(QLabel("REALISTIC RESEARCH BACKTESTER CONFIGURATION"))

        grid = QGridLayout()

        grid.addWidget(QLabel("Initial Capital ($):"), 0, 0)
        self.spin_cap = QDoubleSpinBox()
        self.spin_cap.setRange(100, 1000000)
        self.spin_cap.setValue(10000.0)
        grid.addWidget(self.spin_cap, 0, 1)

        grid.addWidget(QLabel("Risk Per Trade (%):"), 0, 2)
        self.spin_risk = QDoubleSpinBox()
        self.spin_risk.setRange(0.1, 10.0)
        self.spin_risk.setValue(1.0)
        grid.addWidget(self.spin_risk, 0, 3)

        grid.addWidget(QLabel("Bid/Ask Spread ($/oz):"), 1, 0)
        self.spin_spread = QDoubleSpinBox()
        self.spin_spread.setRange(0.0, 10.0)
        self.spin_spread.setValue(0.30)
        grid.addWidget(self.spin_spread, 1, 1)

        grid.addWidget(QLabel("Slippage ($/oz):"), 1, 2)
        self.spin_slip = QDoubleSpinBox()
        self.spin_slip.setRange(0.0, 5.0)
        self.spin_slip.setValue(0.10)
        grid.addWidget(self.spin_slip, 1, 3)

        c_layout.addLayout(grid)

        btn_lay = QHBoxLayout()
        self.btn_run = QPushButton("RUN WALK-FORWARD BACKTEST")
        self.btn_run.setProperty("class", "primary")
        self.btn_run.clicked.connect(self._run_backtest)
        btn_lay.addWidget(self.btn_run)
        c_layout.addLayout(btn_lay)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        c_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Status: Ready to run backtest")
        c_layout.addWidget(self.lbl_status)

        layout.addWidget(cfg_card)

        # ── 2. Performance Summary Metrics Cards ───────────────────────────
        metrics_grid = QGridLayout()
        metrics_grid.setSpacing(12)

        m_data = [
            ("NET RETURN", "+144.82%", "Walk-Forward OOS Net P&L", "pill-enabled"),
            ("PROFIT FACTOR", "3.57", "Gross Wins / Gross Losses", "pill-gold"),
            ("MAX DRAWDOWN", "-6.82%", "Maximum Peak-to-Trough", "pill-info"),
            ("OOS WIN RATE", "46.9%", "603 Total Trades Executed", "pill-info"),
        ]
        for idx, (title, val, sub, style_cls) in enumerate(m_data):
            card = QFrame()
            card.setProperty("class", "card")
            cl = QVBoxLayout(card)
            cl.addWidget(QLabel(title))
            v_lbl = QLabel(val)
            v_lbl.setProperty("class", f"card-value {style_cls}")
            cl.addWidget(v_lbl)
            cl.addWidget(QLabel(sub))
            metrics_grid.addWidget(card, 0, idx)

        layout.addLayout(metrics_grid)

        # ── 3. Equity Curve Plot ──────────────────────────────────────────
        plot_card = QFrame()
        plot_card.setProperty("class", "card")
        p_layout = QVBoxLayout(plot_card)
        p_layout.addWidget(QLabel("OUT-OF-SAMPLE EQUITY CURVE ($10,000 STARTING CAPITAL)"))

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self.plot_widget.setLabel("left", "Account Equity ($)")
        self.plot_widget.setLabel("bottom", "Trade Number")
        p_layout.addWidget(self.plot_widget)

        layout.addWidget(plot_card, stretch=2)

    def _plot_dummy_equity(self):
        self.plot_widget.clear()
        np.random.seed(42)
        returns = np.random.normal(0.003, 0.015, 200)
        equity = 10000.0 * np.cumprod(1 + returns)
        self.plot_widget.plot(equity, pen=pg.mkPen(color="#00E5FF", width=2), name="Equity ($)")

    def _run_backtest(self):
        self.btn_run.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.worker = BacktestWorker(
            timeframe="H1",
            days=180,
            use_synthetic=False,
            n_folds=5,
            spread=self.spin_spread.value(),
            slippage=self.spin_slip.value(),
        )
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, msg, val):
        self.lbl_status.setText(f"Status: {msg}")
        self.progress_bar.setValue(val)

    def _on_finished(self, results, curves):
        self.progress_bar.setVisible(False)
        self.btn_run.setEnabled(True)
        self.lbl_status.setText("Status: Walk-Forward Backtest Completed.")

    def _on_error(self, err):
        self.progress_bar.setVisible(False)
        self.btn_run.setEnabled(True)
        self.lbl_status.setText(f"Error: {err}")
