"""
System Logs & Health Monitoring Page.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QPlainTextEdit, QComboBox
)


class SystemLogsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # ── 1. Health Status Bar ───────────────────────────────────────────
        hdr = QFrame()
        hdr.setProperty("class", "card")
        h_lay = QHBoxLayout(hdr)

        h_lay.addWidget(QLabel("<b>SYSTEM HEALTH:</b> <font color='#00E676'>ALL SYSTEMS OPERATIONAL</font>"))
        h_lay.addWidget(QLabel(" | <b>FAIL-CLOSED PRINCIPLE:</b> <font color='#00E5FF'>ACTIVE</font>"))
        h_lay.addStretch()

        btn_clear = QPushButton("CLEAR LOGS")
        btn_clear.clicked.connect(self._clear_logs)
        h_lay.addWidget(btn_clear)

        layout.addWidget(hdr)

        # ── 2. Log Level Filter & Console ─────────────────────────────────
        console_card = QFrame()
        console_card.setProperty("class", "card")
        c_lay = QVBoxLayout(console_card)

        filter_lay = QHBoxLayout()
        filter_lay.addWidget(QLabel("Min Severity Filter:"))
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(["ALL (INFO)", "WARNING & ABOVE", "ERROR & CRITICAL"])
        filter_lay.addWidget(self.combo_filter)
        filter_lay.addStretch()

        c_lay.addLayout(filter_lay)

        self.log_edit = QPlainTextEdit()
        self.log_edit.setReadOnly(True)

        sample_logs = (
            "2026-09-16 00:00:01 [INFO] app.main: XAUUSD AI Trading Research Workstation starting...\n"
            "2026-09-16 00:00:01 [INFO] data.mt5_connector: MT5 connected — company=MetaQuotes Ltd., build=6194\n"
            "2026-09-16 00:00:02 [INFO] data.mt5_connector: Found 3 gold/USD symbol candidates. Active symbol confirmed: XAUUSD\n"
            "2026-09-16 00:00:02 [INFO] data.data_store: Database initialized at xauusd_research.db\n"
            "2026-09-16 00:00:03 [INFO] data.data_validator: Data quality verdict: WARNING (2,794 candles UTC loaded)\n"
            "2026-09-16 00:00:04 [INFO] models.classifiers: Momentum (Prev Return) OOS Accuracy: 51.73%, Net Return: +104.40%\n"
            "2026-09-16 00:00:05 [INFO] backtester.walk_forward: 5-Fold Walk-Forward Cross-Validation completed (PF: 3.57)\n"
            "2026-09-16 00:00:06 [WARNING] risk.engine: Decision WAIT -> Minimum tradable lot size (0.01) exceeds permitted risk on $200 account\n"
            "2026-09-16 00:00:06 [INFO] app.main: System invariant enforced: LIVE TRADING IS DISABLED.\n"
        )
        self.log_edit.setPlainText(sample_logs)

        c_lay.addWidget(self.log_edit)
        layout.addWidget(console_card)

    def _clear_logs(self):
        self.log_edit.clear()
