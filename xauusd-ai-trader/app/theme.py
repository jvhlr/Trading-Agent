"""
XAUUSD AI Trading Research Workstation — UI Theme & Stylesheet

Defines a dark, professional quantitative workstation aesthetic:
- Deep slate background (#121418)
- Surface elevation card panels (#1A1D24)
- Subtle borders (#2A2F3D)
- Quantitative color accents:
    - Cyan (#00E5FF) -> Primary branding / Highlights
    - Gold (#FFD700) -> XAUUSD accent
    - Emerald (#00E676) -> Positive returns / Pass / Buy
    - Rose (#FF5252) -> Negative returns / Fail / Sell / Warnings
    - Amber (#FFAB00) -> Wait / Warnings / Caution
"""

DARK_STYLESHEET = """
QMainWindow {
    background-color: #121418;
    color: #E0E6ED;
    font-family: 'Segoe UI', 'SF Pro Text', -apple-system, Roboto, sans-serif;
    font-size: 13px;
}

QWidget {
    background-color: #121418;
    color: #E0E6ED;
}

/* Sidebar Navigation */
QListWidget#sidebar {
    background-color: #161920;
    border: none;
    border-right: 1px solid #2A2F3D;
    outline: none;
    padding-top: 8px;
}

QListWidget#sidebar::item {
    height: 38px;
    padding-left: 14px;
    color: #90A0B7;
    font-weight: 500;
    border-left: 3px solid transparent;
}

QListWidget#sidebar::item:hover {
    background-color: #1E232E;
    color: #FFFFFF;
}

QListWidget#sidebar::item:selected {
    background-color: #1E232E;
    color: #00E5FF;
    border-left: 3px solid #00E5FF;
    font-weight: 600;
}

/* Header Status Bar */
QFrame#top_bar {
    background-color: #161920;
    border-bottom: 1px solid #2A2F3D;
    min-height: 48px;
    max-height: 48px;
}

QLabel.status-pill {
    background-color: #1E232E;
    border: 1px solid #2A2F3D;
    border-radius: 4px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 600;
}

QLabel.pill-disabled {
    color: #FF5252;
    background-color: #2D1B22;
    border: 1px solid #7F2634;
}

QLabel.pill-enabled {
    color: #00E676;
    background-color: #1B2D24;
    border: 1px solid #267F4B;
}

QLabel.pill-info {
    color: #00E5FF;
    background-color: #1A2836;
    border: 1px solid #1E4E66;
}

QLabel.pill-gold {
    color: #FFD700;
    background-color: #2E2818;
    border: 1px solid #66551E;
}

/* Card Panels */
QFrame.card {
    background-color: #1A1D24;
    border: 1px solid #2A2F3D;
    border-radius: 6px;
    padding: 12px;
}

QFrame.card:hover {
    border: 1px solid #3A4257;
}

/* Headings */
QLabel.card-title {
    font-size: 11px;
    font-weight: 700;
    color: #7889A4;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

QLabel.card-value {
    font-size: 22px;
    font-weight: 700;
    color: #FFFFFF;
}

QLabel.card-subtext {
    font-size: 11px;
    color: #90A0B7;
}

/* Tables */
QTableWidget {
    background-color: #161920;
    border: 1px solid #2A2F3D;
    gridline-color: #242936;
    border-radius: 4px;
    color: #E0E6ED;
}

QTableWidget::item {
    padding: 6px 10px;
}

QTableWidget::item:selected {
    background-color: #242E42;
    color: #00E5FF;
}

QHeaderView::section {
    background-color: #1E232E;
    color: #90A0B7;
    font-weight: 600;
    font-size: 11px;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #2A2F3D;
    text-transform: uppercase;
}

/* Buttons */
QPushButton {
    background-color: #242A38;
    border: 1px solid #363F54;
    color: #E0E6ED;
    border-radius: 4px;
    padding: 7px 14px;
    font-weight: 600;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #2E364A;
    border-color: #00E5FF;
    color: #FFFFFF;
}

QPushButton:pressed {
    background-color: #1A2130;
}

QPushButton.primary {
    background-color: #007ACC;
    border: 1px solid #0099FF;
    color: #FFFFFF;
}

QPushButton.primary:hover {
    background-color: #008AE6;
}

QPushButton.danger {
    background-color: #801B24;
    border: 1px solid #B32433;
    color: #FFFFFF;
}

QPushButton.danger:hover {
    background-color: #A3222E;
}

/* Input controls */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background-color: #161920;
    border: 1px solid #2A2F3D;
    border-radius: 4px;
    padding: 6px 10px;
    color: #FFFFFF;
}

QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 1px solid #00E5FF;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

/* Scrollbars */
QScrollBar:vertical {
    background: #121418;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #2A2F3D;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #454F68;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QTextEdit, QPlainTextEdit {
    background-color: #121418;
    border: 1px solid #2A2F3D;
    color: #C5D1E0;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}
"""
