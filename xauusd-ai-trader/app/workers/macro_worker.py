"""
Background Worker for Asynchronous Macroeconomic Data Collection.
"""

from PySide6.QtCore import QThread, Signal
import yfinance as yf
import traceback
import logging

logger = logging.getLogger(__name__)

class MacroFetchWorker(QThread):
    """Worker thread for non-blocking macro data collection using yfinance."""
    # Emits dict with structure: { "DXY": {"val": "104.12", "chg": "+0.18%"}, ... }
    finished_signal = Signal(dict)
    error_signal = Signal(str)

    def __init__(self):
        super().__init__()
        # Map of our internal keys to Yahoo Finance tickers
        self.tickers = {
            "DXY": "DX-Y.NYB",
            "US10Y": "^TNX",
            "US2Y": "^IRX",
            "VIX": "^VIX",
            "XAG": "SI=F",
            "BRENT": "BZ=F",
        }

    def run(self):
        try:
            results = {}
            for key, ticker in self.tickers.items():
                try:
                    # Download last 2 days to calculate daily change
                    data = yf.download(ticker, period="2d", interval="1d", progress=False)
                    
                    if len(data) >= 2:
                        # yfinance sometimes returns a DataFrame for 'Close' with the ticker as column
                        close_col = data['Close']
                        if close_col.ndim > 1:
                            prev_close = float(close_col.iloc[-2, 0])
                            curr_close = float(close_col.iloc[-1, 0])
                        else:
                            prev_close = float(close_col.iloc[-2])
                            curr_close = float(close_col.iloc[-1])
                            
                        chg_pct = ((curr_close - prev_close) / prev_close) * 100
                        chg_val = curr_close - prev_close
                        val_str = f"{curr_close:.2f}"
                        chg_str = f"{chg_pct:+.2f}%"
                        
                        # Formatting based on instrument type
                        if key in ["US10Y", "US2Y"]:
                            val_str = f"{curr_close:.2f}%"
                            # For yields, show bps change or absolute change
                            chg_str = f"{chg_val:+.2f}%" 
                        elif key == "DXY":
                            val_str = f"{curr_close:.2f}"
                            chg_str = f"{chg_pct:+.2f}%"
                        elif key == "VIX":
                            val_str = f"{curr_close:.2f}"
                            chg_str = f"{chg_val:+.2f}"
                        elif key == "XAG":
                            val_str = f"${curr_close:.2f}"
                            chg_str = f"{chg_pct:+.2f}%"
                        elif key == "BRENT":
                            val_str = f"${curr_close:.2f}"
                            chg_str = f"{chg_pct:+.2f}%"
                            
                        results[key] = {"val": val_str, "chg": chg_str}
                    else:
                        results[key] = {"val": "N/A", "chg": "N/A"}
                except Exception as e:
                    logger.warning(f"Failed to fetch {ticker}: {e}")
                    results[key] = {"val": "N/A", "chg": "N/A"}
            
            self.finished_signal.emit(results)
        except Exception as e:
            logger.error(f"MacroFetchWorker error: {traceback.format_exc()}")
            self.error_signal.emit(str(e))
