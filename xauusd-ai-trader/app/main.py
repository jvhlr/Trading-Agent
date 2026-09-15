"""
XAUUSD AI Trading Research Workstation — Desktop Application Entry Point.

Usage:
    py app/main.py
"""

import sys
import logging
from pathlib import Path

# Add project root to sys.path so backend imports work cleanly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app.theme import DARK_STYLESHEET
from app.ui.main_window import MainWindow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("Initializing XAUUSD AI Trading Workstation Desktop GUI...")
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLESHEET)

    window = MainWindow()
    window.show()

    logger.info("GUI event loop started.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
