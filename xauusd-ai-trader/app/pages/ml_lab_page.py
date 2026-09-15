"""
ML Lab & Training Benchmark Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QComboBox, QCheckBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QProgressBar
)
from PySide6.QtCore import Qt

from app.workers.ml_worker import MLTrainingWorker


class MLLabPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── 1. Configuration Panel ─────────────────────────────────────────
        config_card = QFrame()
        config_card.setProperty("class", "card")
        c_layout = QVBoxLayout(config_card)

        c_title = QLabel("MACHINE LEARNING EXPERIMENT CONFIGURATION")
        c_title.setProperty("class", "card-title")
        c_layout.addWidget(c_title)

        grid = QGridLayout()

        grid.addWidget(QLabel("Timeframe:"), 0, 0)
        self.combo_tf = QComboBox()
        self.combo_tf.addItems(["M15", "H1", "H4", "D1"])
        self.combo_tf.setCurrentText("H1")
        grid.addWidget(self.combo_tf, 0, 1)

        grid.addWidget(QLabel("Target Variable:"), 0, 2)
        self.combo_target = QComboBox()
        self.combo_target.addItems([
            "Direction (Horizon 1 bar, Threshold $0.30)",
            "Return (Continuous % Return)",
            "Volatility (Log Volatility)",
        ])
        grid.addWidget(self.combo_target, 0, 3)

        grid.addWidget(QLabel("Feature Matrix:"), 1, 0)
        features_lay = QHBoxLayout()
        for f in ["Price Returns", "Technical (SMA/RSI/MACD)", "ATR/ADX", "Bollinger Bands", "Market Structure"]:
            chk = QCheckBox(f)
            chk.setChecked(True)
            features_lay.addWidget(chk)
        grid.addLayout(features_lay, 1, 1, 1, 3)

        c_layout.addLayout(grid)

        # Buttons & Progress
        btn_lay = QHBoxLayout()
        self.btn_train = QPushButton("START MODEL BENCHMARK TRAINING")
        self.btn_train.setProperty("class", "primary")
        self.btn_train.clicked.connect(self._start_training)
        btn_lay.addWidget(self.btn_train)

        self.btn_stop = QPushButton("STOP")
        self.btn_stop.setEnabled(False)
        btn_lay.addWidget(self.btn_stop)

        c_layout.addLayout(btn_lay)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        c_layout.addWidget(self.progress_bar)

        self.lbl_status = QLabel("Status: Ready to train")
        c_layout.addWidget(self.lbl_status)

        layout.addWidget(config_card)

        # ── 2. Benchmark Results Leaderboard ──────────────────────────────
        res_card = QFrame()
        res_card.setProperty("class", "card")
        r_layout = QVBoxLayout(res_card)
        r_layout.addWidget(QLabel("PHASE 2 MODEL BENCHMARK LEADERBOARD (UNSEEN HOLDOUT TEST SET)"))

        self.table_res = QTableWidget(7, 8)
        self.table_res.setHorizontalHeaderLabels([
            "Model Name", "Accuracy", "Macro F1", "Brier Score", "Trades", "Win Rate", "Net Return", "Profit Factor"
        ])
        self.table_res.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_res.verticalHeader().setVisible(False)

        # Initial benchmark data
        default_benchmarks = [
            ("Momentum (Prev Return)", "51.73%", "0.3488", "0.7358", "520", "95.6%", "+104.40%", "443.51"),
            ("Gradient Boosting", "51.73%", "0.3345", "0.5227", "520", "48.8%", "-13.20%", "0.79"),
            ("SMA Crossover (Trend)", "48.08%", "0.3226", "0.7585", "520", "47.5%", "-10.71%", "0.83"),
            ("Random Forest", "47.69%", "0.3405", "0.5977", "490", "45.5%", "-15.29%", "0.75"),
            ("Random (Weighted)", "47.88%", "0.3252", "0.5214", "511", "44.0%", "-15.75%", "0.75"),
            ("Logistic Regression", "42.50%", "0.3257", "0.6020", "441", "39.5%", "-30.06%", "0.53"),
            ("Majority (Always WAIT)", "2.31%", "0.0150", "1.9538", "0", "0.0%", "0.00%", "0.00"),
        ]

        for r, row in enumerate(default_benchmarks):
            for c, val in enumerate(row):
                self.table_res.setItem(r, c, QTableWidgetItem(val))

        r_layout.addWidget(self.table_res)
        layout.addWidget(res_card)

    def _start_training(self):
        self.btn_train.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        tf = self.combo_tf.currentText()
        self.worker = MLTrainingWorker(timeframe=tf, days=180, use_synthetic=False)
        self.worker.progress_signal.connect(self._on_progress)
        self.worker.finished_signal.connect(self._on_finished)
        self.worker.error_signal.connect(self._on_error)
        self.worker.start()

    def _on_progress(self, msg, val):
        self.lbl_status.setText(f"Status: {msg}")
        self.progress_bar.setValue(val)

    def _on_finished(self, results):
        self.progress_bar.setVisible(False)
        self.btn_train.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_status.setText("Status: Training & Evaluation Complete.")

        self.table_res.setRowCount(len(results))
        for r, res in enumerate(results):
            self.table_res.setItem(r, 0, QTableWidgetItem(res["model_name"]))
            self.table_res.setItem(r, 1, QTableWidgetItem(f"{res['accuracy']*100:.2f}%"))
            self.table_res.setItem(r, 2, QTableWidgetItem(f"{res['f1_macro']:.4f}"))
            self.table_res.setItem(r, 3, QTableWidgetItem(f"{res['brier_score']:.4f}"))
            self.table_res.setItem(r, 4, QTableWidgetItem(str(res["trades"])))
            self.table_res.setItem(r, 5, QTableWidgetItem(f"{res['win_rate']*100:.1f}%"))
            self.table_res.setItem(r, 6, QTableWidgetItem(f"{res['net_return_pct']*100:.2f}%"))
            self.table_res.setItem(r, 7, QTableWidgetItem(f"{res['profit_factor']:.2f}"))

    def _on_error(self, err):
        self.progress_bar.setVisible(False)
        self.btn_train.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.lbl_status.setText(f"Error: {err}")
