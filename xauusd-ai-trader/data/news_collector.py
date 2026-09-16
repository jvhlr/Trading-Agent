import logging
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False
    
logger = logging.getLogger(__name__)

class NewsCollector:
    """
    Ingests financial news headlines for Gold and US Dollar from yfinance
    and scores their sentiment using NLP.
    """
    
    def __init__(self, symbols: tuple[str, ...] = ("GC=F", "DX=F")):
        self.symbols = symbols
        if not TEXTBLOB_AVAILABLE:
            logger.warning("TextBlob not available. Sentiment scoring will be zeroed out. Install with: pip install textblob")
            
    def fetch_latest_news(self) -> pd.DataFrame:
        """
        Fetches the latest news articles for the configured symbols.
        Returns a DataFrame with columns: [timestamp, symbol, title, publisher, sentiment, url]
        """
        all_news = []
        
        for sym in self.symbols:
            try:
                ticker = yf.Ticker(sym)
                news = ticker.news
                if not news:
                    continue
                    
                for item in news:
                    # yfinance news schema
                    title = item.get("title", "")
                    content = item.get("content", {})
                    if not title and content:
                        title = content.get("title", "")
                        
                    pub_date = item.get("pubDate") or content.get("pubDate")
                    if pub_date:
                        try:
                            # Handle ISO format from yfinance
                            dt = pd.to_datetime(pub_date, utc=True)
                        except Exception:
                            dt = datetime.now(timezone.utc)
                    else:
                        dt = datetime.now(timezone.utc)
                        
                    publisher = "Unknown"
                    provider = item.get("provider") or content.get("provider")
                    if provider and isinstance(provider, dict):
                        publisher = provider.get("displayName", "Unknown")
                        
                    link = ""
                    url_obj = item.get("canonicalUrl") or content.get("canonicalUrl")
                    if url_obj and isinstance(url_obj, dict):
                        link = url_obj.get("url", "")
                        
                    # Basic Sentiment Analysis
                    sentiment = 0.0
                    if TEXTBLOB_AVAILABLE and title:
                        # VADER-style polarity (-1.0 to 1.0)
                        blob = TextBlob(title)
                        sentiment = blob.sentiment.polarity
                        
                    all_news.append({
                        "timestamp": dt,
                        "symbol": sym,
                        "title": title,
                        "publisher": publisher,
                        "sentiment": sentiment,
                        "url": link
                    })
                    
            except Exception as e:
                logger.error(f"Error fetching news for {sym}: {e}")
                
        if not all_news:
            return pd.DataFrame(columns=["timestamp", "symbol", "title", "publisher", "sentiment", "url"])
            
        df = pd.DataFrame(all_news)
        # Sort descending by time
        df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
        return df

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = NewsCollector()
    df = collector.fetch_latest_news()
    print(df)
