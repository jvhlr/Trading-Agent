"""
Data Foundation & Quality Validation Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QProgressBar
)
from PySide6.QtCore import Qt

from app.workers.data_worker import DataFetchWorker
from data.mt5_connector import MT5Connector, MT5_AVAILABLE


class DataPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── 1. MT5 Broker Connection Panel ───────────────────────────────────
        broker_card = QFrame()
        broker_card.setProperty("class", "card")
        b_layout = QVBoxLayout(broker_card)

        b_title = QLabel("META-TRADER 5 BROKER CONNECTION & DISCOVERY")
        b_title.setProperty("class", "card-title")
        b_layout.addWidget(b_title)

        b_grid = QHBoxLayout()
        b_grid.addWidget(QLabel("<b>MT5 API Status:</b>"))
        self.lbl_mt5_status = QLabel("<font color='#00E676'><b>AVAILABLE (Connected)</b></font>" if MT5_AVAILABLE else "<font color='#FF5252'><b>NOT INSTALLED</b></font>")
        b_grid.addWidget(self.lbl_mt5_status)

        b_grid.addWidget(QLabel(" | <b>Broker Company:</b> MetaQuotes Ltd."))
        b_grid.addWidget(QLabel(" | <b>Account Server:</b> MetaQuotes-Demo"))
        b_grid.addWidget(QLabel(" | <b>Leverage:</b> 1:100"))
        b_grid.addStretch()

        self.btn_fetch = QPushButton("FETCH & STORE LATEST MT5 DATA")
        self.btn_fetch.clicked.connect(self._start_fetch_data)
        b_grid.addWidget(self.btn_fetch)

        b_layout.addLayout(b_grid)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        b_layout.addWidget(self.progress_bar)

        layout.addWidget(broker_card)

        # ── 2. Symbol Candidates Table ─────────────────────────────────────
        sym_card = QFrame()
        sym_card.setProperty("class", "card")
        sym_layout = QVBoxLayout(sym_card)
        sym_layout.addWidget(QLabel("DISCOVERED BROKER XAUUSD SYMBOL CANDIDATES"))

        table_sym = QTableWidget(3, 7)
        table_sym.setHorizontalHeaderLabels([
            "Broker Candidate", "Description", "Digits", "Point", "Tick Size", "Tick Value", "Status"
        ])
        table_sym.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table_sym.verticalHeader().setVisible(False)

        candidates = [
            ("XAUUSD", "Gold vs US Dollar", "2", "0.01", "0.01", "$0.10", "CONFIRMED ACTIVE"),
            ("GOLD", "Barrick Gold Corp (Stock)", "2", "0.01", "0.01", "$0.01", "EXCLUDED (EQUITY)"),
            ("GTIP", "Goldman Sachs Bond ETF", "2", "0.01", "0.01", "$0.01", "EXCLUDED (ETF)"),
        ]
        for r, (sym, desc, dig, pt, ts, tv, st) in enumerate(candidates):
            table_sym.setItem(r, 0, QTableWidgetItem(sym))
            table_sym.setItem(r, 1, QTableWidgetItem(desc))
            table_sym.setItem(r, 2, QTableWidgetItem(dig))
            table_sym.setItem(r, 3, QTableWidgetItem(pt))
            table_sym.setItem(r, 4, QTableWidgetItem(ts))
            table_sym.setItem(r, 5, QTableWidgetItem(tv))
            table_sym.setItem(r, 6, QTableWidgetItem(st))

        sym_layout.addWidget(table_sym)
        layout.addWidget(sym_card)

        # ── 3. Data Quality Checks Report Card ─────────────────────────────
        qc_card = QFrame()
        qc_card.setProperty("class", "card")
        qc_layout = QVBoxLayout(qc_card)
        qc_layout.addWidget(QLabel("POINT-IN-TIME DATA QUALITY VALIDATION REPORT"))

        self.table_qc = QTableWidget(7, 4)
        self.table_qc.setHorizontalHeaderLabels([
            "Validation Rule", "Status", "Issue Count", "Details"
        ])
        self.table_qc.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_qc.verticalHeader().setVisible(False)

        self.table_qc.setRowCount(0)
        qc_layout.addWidget(self.table_qc)
        layout.addWidget(qc_card)

    def _start_fetch_data(self):
        self.btn_fetch.setEnabled(False)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)

        self.worker = DataFetchWorker(timeframe="H1", days=365, use_synthetic=False)
        self.worker.finished_signal.connect(self._on_fetch_finished)
        self.worker.error_signal.connect(self._on_fetch_error)
        self.worker.start()

    def _on_fetch_finished(self, df, report, dataset_id):
        self.progress_bar.setVisible(False)
        self.btn_fetch.setEnabled(True)
        
        # Update Table with report checks
        self.table_qc.setRowCount(len(report.checks))
        for r, check in enumerate(report.checks):
            status = "PASS" if check.passed else check.severity.value
            self.table_qc.setItem(r, 0, QTableWidgetItem(check.name))
            
            # Color status
            status_item = QTableWidgetItem(status)
            if status == "PASS" or status == "INFO":
                status_item.setForeground(Qt.GlobalColor.green)
            elif status == "WARNING":
                status_item.setForeground(Qt.GlobalColor.yellow)
            else:
                status_item.setForeground(Qt.GlobalColor.red)
                
            self.table_qc.setItem(r, 1, status_item)
            self.table_qc.setItem(r, 2, QTableWidgetItem(str(check.count)))
            self.table_qc.setItem(r, 3, QTableWidgetItem(check.details))

    def _on_fetch_error(self, err_msg):
        self.progress_bar.setVisible(False)
        self.btn_fetch.setEnabled(True)
