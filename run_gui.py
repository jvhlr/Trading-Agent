"""
XAUUSD AI Trading Research Workstation — Root Launcher.
"""

import sys
import os
from pathlib import Path

# Add xauusd-ai-trader to sys.path
PROJECT_DIR = Path(__file__).resolve().parent / "xauusd-ai-trader"
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Change current working directory to project directory
os.chdir(str(PROJECT_DIR))

# Launch desktop app
from app.main import main

if __name__ == "__main__":
    main()
