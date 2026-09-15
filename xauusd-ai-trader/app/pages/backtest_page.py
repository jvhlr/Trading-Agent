"""
Research Backtester Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QDoubleSpinBox, QSpinBox, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar
)
from PySide6.QtWebEngineWidgets import QWebEngineView
import numpy as np
import json
import os

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
        self.metric_labels = []
        for idx, (title, val, sub, style_cls) in enumerate(m_data):
            card = QFrame()
            card.setProperty("class", "card")
            cl = QVBoxLayout(card)
            cl.addWidget(QLabel(title))
            v_lbl = QLabel(val)
            v_lbl.setProperty("class", f"card-value {style_cls}")
            self.metric_labels.append(v_lbl)
            cl.addWidget(v_lbl)
            cl.addWidget(QLabel(sub))
            metrics_grid.addWidget(card, 0, idx)

        layout.addLayout(metrics_grid)

        # ── 3. Equity Curve Plot ──────────────────────────────────────────
        plot_card = QFrame()
        plot_card.setProperty("class", "card")
        p_layout = QVBoxLayout(plot_card)
        p_layout.addWidget(QLabel("OUT-OF-SAMPLE EQUITY CURVE ($10,000 STARTING CAPITAL)"))

        self.web_view = QWebEngineView()
        # Load local HTML file
        template_path = os.path.join(os.path.dirname(__file__), "..", "templates", "tv_line.html")
        self.web_view.load(f"file:///{template_path.replace(chr(92), '/')}")
        p_layout.addWidget(self.web_view)

        layout.addWidget(plot_card, stretch=2)

    def _plot_dummy_equity(self):
        # We don't plot dummy data here because the webview needs time to load.
        # It's better to just let it sit blank or display its default state.
        pass

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
        
        # Find best model
        if results:
            best = max(results, key=lambda x: x["net_return_pct"])
            self.lbl_status.setText(f"Status: Walk-Forward Backtest Completed. Best Model: {best['model_name']}")
            self.metric_labels[0].setText(f"+{best['net_return_pct']*100:.2f}%")
            self.metric_labels[1].setText(f"{best['profit_factor']:.2f}")
            mdd = best.get("max_drawdown", 0.0)
            self.metric_labels[2].setText(f"{mdd*100:.2f}%")
            self.metric_labels[3].setText(f"{best['win_rate']*100:.1f}%\n{best['total_trades']} Total Trades Executed")
            
            eq_curve = best.get("equity_curve", [])
            if len(eq_curve) > 0:
                # Convert to TradingView format
                tv_data = [{"time": i + 1, "value": round(val, 2)} for i, val in enumerate(eq_curve)]
                json_data = json.dumps(tv_data)
                self.web_view.page().runJavaScript(f"updateData({json_data})")
        else:
            self.lbl_status.setText("Status: Walk-Forward Backtest Completed (No Results).")


    def _on_error(self, err):
        self.progress_bar.setVisible(False)
        self.btn_run.setEnabled(True)
        self.lbl_status.setText(f"Error: {err}")
