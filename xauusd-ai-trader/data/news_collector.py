"""
XAUUSD AI Trading Research System — FXStreet News Collector

Fetches real-time Forex & Commodities headlines from FXStreet's public RSS feed
and scores their sentiment using TextBlob NLP.
"""

import logging
import xml.etree.ElementTree as ET
import urllib.request
import pandas as pd
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except ImportError:
    TEXTBLOB_AVAILABLE = False

logger = logging.getLogger(__name__)

# FXStreet RSS endpoints
FXSTREET_NEWS_RSS = "https://www.fxstreet.com/rss/news"

# Gold / USD keyword filters for relevance scoring
GOLD_KEYWORDS = {"gold", "xau", "xauusd", "bullion", "precious metal", "safe haven", "safe-haven"}
USD_KEYWORDS = {"usd", "dollar", "dxy", "fed", "fomc", "nfp", "cpi", "ppi", "treasury", "yield", "inflation"}


class NewsCollector:
    """
    Ingests financial news headlines from FXStreet RSS and scores
    their sentiment using NLP (TextBlob).
    """

    def __init__(self):
        if not TEXTBLOB_AVAILABLE:
            logger.warning(
                "TextBlob not available. Sentiment scoring will be zeroed out. "
                "Install with: pip install textblob"
            )

    def fetch_latest_news(self) -> pd.DataFrame:
        """
        Fetches the latest news articles from FXStreet RSS.
        Returns a DataFrame with columns:
            [timestamp, title, description, sentiment, relevance, url]
        """
        all_news = []

        try:
            req = urllib.request.Request(
                FXSTREET_NEWS_RSS,
                headers={"User-Agent": "Mozilla/5.0 (XAUUSD-AI-Trader Research Bot)"},
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                xml_bytes = resp.read()

            root = ET.fromstring(xml_bytes)
            channel = root.find("channel")
            if channel is None:
                logger.warning("FXStreet RSS: No <channel> element found.")
                return self._empty_df()

            for item in channel.findall("item"):
                title_el = item.find("title")
                desc_el = item.find("description")
                link_el = item.find("link")
                pub_el = item.find("pubDate")

                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                description = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
                url = link_el.text.strip() if link_el is not None and link_el.text else ""

                # Parse RFC-2822 date
                dt = datetime.now(timezone.utc)
                if pub_el is not None and pub_el.text:
                    try:
                        dt = parsedate_to_datetime(pub_el.text.strip())
                    except Exception:
                        pass

                # Sentiment analysis on title + description
                sentiment = 0.0
                if TEXTBLOB_AVAILABLE and title:
                    combined_text = f"{title}. {description}" if description else title
                    blob = TextBlob(combined_text)
                    sentiment = blob.sentiment.polarity

                # Relevance tagging
                relevance = self._compute_relevance(title, description)

                all_news.append({
                    "timestamp": dt,
                    "title": title,
                    "description": description,
                    "sentiment": sentiment,
                    "relevance": relevance,
                    "url": url,
                })

        except Exception as e:
            logger.error(f"Error fetching FXStreet RSS: {e}")

        if not all_news:
            return self._empty_df()

        df = pd.DataFrame(all_news)
        df = df.sort_values("timestamp", ascending=False).reset_index(drop=True)
        return df

    @staticmethod
    def _compute_relevance(title: str, description: str) -> str:
        """
        Tags each headline with a relevance category for XAUUSD trading:
            GOLD_DIRECT, USD_RELATED, MACRO, or GENERAL
        """
        combined = (title + " " + description).lower()

        if any(kw in combined for kw in GOLD_KEYWORDS):
            return "GOLD_DIRECT"
        if any(kw in combined for kw in USD_KEYWORDS):
            return "USD_RELATED"
        # Broader macro keywords
        macro_kw = {"rate decision", "central bank", "ecb", "boj", "pboc", "oil", "brent", "geopolitical"}
        if any(kw in combined for kw in macro_kw):
            return "MACRO"
        return "GENERAL"

    @staticmethod
    def _empty_df() -> pd.DataFrame:
        return pd.DataFrame(
            columns=["timestamp", "title", "description", "sentiment", "relevance", "url"]
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = NewsCollector()
    df = collector.fetch_latest_news()
    print(f"Fetched {len(df)} headlines from FXStreet RSS\n")
    for _, row in df.head(10).iterrows():
        rel = row["relevance"]
        sent = row["sentiment"]
        print(f"  [{rel:12s}] (sent={sent:+.2f}) {row['title'][:80]}")
