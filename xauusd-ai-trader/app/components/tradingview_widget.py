"""
TradingView Interactive Chart Widget using QWebEngineView.
"""

from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QUrl

class TradingViewWidget(QWidget):
    def __init__(self, symbol="OANDA:XAUUSD", interval="60", theme="dark", parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.interval = interval
        self.theme = theme
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.web_view = QWebEngineView()
        self.main_layout.addWidget(self.web_view)
        
        self.load_chart()

    def load_chart(self):
        """Loads the TradingView Advanced Chart Widget HTML into the WebEngineView."""
        
        # Ensure we construct valid JS strings
        bg_color = "#1A1A1A" if self.theme == "dark" else "#FFFFFF"
        grid_color = "#313131" if self.theme == "dark" else "#E0E0E0"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8" />
            <title>TradingView Chart</title>
            <style>
                html, body {{
                    margin: 0;
                    padding: 0;
                    height: 100%;
                    width: 100%;
                    overflow: hidden;
                    background-color: {bg_color};
                }}
                .tradingview-widget-container {{
                    height: 100%;
                    width: 100%;
                }}
                #tradingview_widget {{
                    height: 100%;
                    width: 100%;
                }}
            </style>
        </head>
        <body>
            <div class="tradingview-widget-container">
                <div id="tradingview_widget"></div>
                <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                <script type="text/javascript">
                new TradingView.widget(
                {{
                    "autosize": true,
                    "symbol": "{self.symbol}",
                    "interval": "{self.interval}",
                    "timezone": "Etc/UTC",
                    "theme": "{self.theme}",
                    "style": "1",
                    "locale": "en",
                    "enable_publishing": false,
                    "backgroundColor": "{bg_color}",
                    "gridColor": "{grid_color}",
                    "hide_top_toolbar": false,
                    "hide_legend": false,
                    "save_image": false,
                    "container_id": "tradingview_widget"
                }}
                );
                </script>
            </div>
        </body>
        </html>
        """
        
        self.web_view.setHtml(html_content, baseUrl=QUrl("https://s3.tradingview.com"))

    def change_symbol(self, new_symbol: str, new_interval: str | None = None):
        """Changes the symbol (and optionally interval) and reloads the chart."""
        self.symbol = new_symbol
        if new_interval:
            self.interval = new_interval
        self.load_chart()
