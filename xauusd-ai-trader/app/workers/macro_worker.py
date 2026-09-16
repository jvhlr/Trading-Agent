"""
Background Worker for Asynchronous Macroeconomic Data Collection via FXStreet RSS.
"""

from PySide6.QtCore import QThread, Signal
import xml.etree.ElementTree as ET
import urllib.request
import re
import traceback
import logging

logger = logging.getLogger(__name__)

# FXStreet RSS feed for all news (includes macro headlines with embedded prices)
FXSTREET_RSS_URL = "https://www.fxstreet.com/rss/news"

# Regex patterns to extract prices from FXStreet headlines/descriptions
PRICE_PATTERNS = {
    "DXY": [
        re.compile(r"(?:DXY|US Dollar Index|Dollar Index)[^\d]*?(\d{2,3}\.\d{1,2})", re.IGNORECASE),
        re.compile(r"(\d{2,3}\.\d{1,2})[^\d]*?(?:DXY|Dollar Index)", re.IGNORECASE),
    ],
    "US10Y": [
        re.compile(r"(?:US\s*10[\-\s]?(?:Year|Y)|10Y)[^\d]*?(\d\.\d{1,3})%?", re.IGNORECASE),
    ],
    "US2Y": [
        re.compile(r"(?:US\s*2[\-\s]?(?:Year|Y)|2Y)[^\d]*?(\d\.\d{1,3})%?", re.IGNORECASE),
    ],
    "VIX": [
        re.compile(r"(?:VIX|CBOE)[^\d]*?(\d{1,2}\.\d{1,2})", re.IGNORECASE),
    ],
    "XAG": [
        re.compile(r"(?:XAG|Silver|XAGUSD)[^\d]*?\$?(\d{1,3}\.\d{1,2})", re.IGNORECASE),
    ],
    "BRENT": [
        re.compile(r"(?:Brent|WTI|Oil|Crude)[^\d]*?\$?(\d{2,3}\.\d{1,2})", re.IGNORECASE),
    ],
}


class MacroFetchWorker(QThread):
    """Worker thread for non-blocking macro data collection using FXStreet RSS."""
    # Emits dict with structure: { "DXY": {"val": "104.12", "chg": "N/A"}, ... }
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self):
        super().__init__()

    def run(self):
        try:
            # Fetch FXStreet RSS
            req = urllib.request.Request(
                FXSTREET_RSS_URL,
                headers={"User-Agent": "Mozilla/5.0 (XAUUSD-AI-Trader Research Bot)"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                xml_bytes = resp.read()

            root = ET.fromstring(xml_bytes)
            channel = root.find("channel")

            # Collect all headline text for price extraction
            all_text_blocks: list[str] = []
            if channel is not None:
                for item in channel.findall("item"):
                    title_el = item.find("title")
                    desc_el = item.find("description")
                    if title_el is not None and title_el.text:
                        all_text_blocks.append(title_el.text)
                    if desc_el is not None and desc_el.text:
                        all_text_blocks.append(desc_el.text)

            combined_text = " ".join(all_text_blocks)

            results: dict[str, dict[str, str]] = {}
            for key, patterns in PRICE_PATTERNS.items():
                val_str = "N/A"
                for pattern in patterns:
                    match = pattern.search(combined_text)
                    if match:
                        raw_val = match.group(1)
                        try:
                            val = float(raw_val)
                            if key in ("US10Y", "US2Y"):
                                val_str = f"{val:.2f}%"
                            elif key in ("XAG", "BRENT"):
                                val_str = f"${val:.2f}"
                            else:
                                val_str = f"{val:.2f}"
                        except ValueError:
                            continue
                        break

                # FXStreet RSS does not provide prior-day close, so change is N/A
                results[key] = {"val": val_str, "chg": "N/A"}

            self.finished_signal.emit(results)
        except Exception as e:
            logger.error(f"MacroFetchWorker error: {traceback.format_exc()}")
            self.error_signal.emit(str(e))
