"""
Tests -- NewsCollector (Phase 5)

TRAP: never hit the real FXStreet RSS in tests.
"""

import sys
import io
import logging
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import pytest
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.news_collector import NewsCollector

EXPECTED_COLUMNS = ["timestamp", "title", "description", "sentiment", "relevance", "url"]

CANNED_RSS = (
    b"<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    b"<rss version=\"2.0\"><channel>"
    b"<item><title>Gold hits record high</title>"
    b"<description>Bullion surges past 2500</description>"
    b"<link>https://example.com/gold-high</link>"
    b"<pubDate>Fri, 03 Jan 2025 13:00:00 +0000</pubDate></item>"
    b"<item><title>Fed holds rates</title>"
    b"<description>FOMC keeps federal funds rate unchanged</description>"
    b"<link>https://example.com/fed-hold</link>"
    b"<pubDate>Thu, 02 Jan 2025 18:00:00 +0000</pubDate></item>"
    b"<item><title>ECB signals caution</title>"
    b"<description>European central bank flags downside risks</description>"
    b"<link>https://example.com/ecb-caution</link>"
    b"<pubDate>Wed, 01 Jan 2025 12:00:00 +0000</pubDate></item>"
    b"</channel></rss>"
)

NO_CHANNEL_RSS = (
    b"<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    b"<rss version=\"2.0\"></rss>"
)

MISSING_FIELDS_RSS = (
    b"<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    b"<rss version=\"2.0\"><channel><item></item></channel></rss>"
)

BAD_DATE_RSS = (
    b"<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    b"<rss version=\"2.0\"><channel>"
    b"<item><title>Some headline</title>"
    b"<description>Something happened</description>"
    b"<link>https://example.com/some</link>"
    b"<pubDate>not-a-valid-date</pubDate></item>"
    b"</channel></rss>"
)

GOLD_BEATS_USD_RSS = (
    b"<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
    b"<rss version=\"2.0\"><channel>"
    b"<item><title>Gold prices fall as Fed raises rates</title>"
    b"<description>Bullion drops on dollar strength</description>"
    b"<link>https://example.com/gold-fed</link>"
    b"<pubDate>Mon, 06 Jan 2025 10:00:00 +0000</pubDate></item>"
    b"</channel></rss>"
)


def _make_urlopen_mock(body: bytes):
    mock_resp = MagicMock()
    mock_resp.read.return_value = body
    mock_resp.__enter__ = lambda s: mock_resp
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestNewsCollectorSchema:
    def test_canned_feed_has_correct_columns(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(CANNED_RSS)):
            collector = NewsCollector()
            df = collector.fetch_latest_news()
        assert list(df.columns) == EXPECTED_COLUMNS

    def test_canned_feed_has_3_rows(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(CANNED_RSS)):
            collector = NewsCollector()
            df = collector.fetch_latest_news()
        assert len(df) == 3

    def test_rows_sorted_newest_first(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(CANNED_RSS)):
            collector = NewsCollector()
            df = collector.fetch_latest_news()
        timestamps = list(df["timestamp"])
        assert timestamps == sorted(timestamps, reverse=True)

    def test_fields_parsed_correctly(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(CANNED_RSS)):
            collector = NewsCollector()
            df = collector.fetch_latest_news()
        top = df.iloc[0]
        assert top["title"] == "Gold hits record high"
        assert top["url"] == "https://example.com/gold-high"
        assert top["description"] == "Bullion surges past 2500"


class TestNewsCollectorRelevance:
    def test_gold_keyword_gives_gold_direct(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(CANNED_RSS)):
            collector = NewsCollector()
            df = collector.fetch_latest_news()
        gold_row = df[df["title"] == "Gold hits record high"].iloc[0]
        assert gold_row["relevance"] == "GOLD_DIRECT"

    def test_fed_keyword_gives_usd_related(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(CANNED_RSS)):
            collector = NewsCollector()
            df = collector.fetch_latest_news()
        fed_row = df[df["title"] == "Fed holds rates"].iloc[0]
        assert fed_row["relevance"] == "USD_RELATED"

    def test_ecb_keyword_gives_macro(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(CANNED_RSS)):
            collector = NewsCollector()
            df = collector.fetch_latest_news()
        ecb_row = df[df["title"] == "ECB signals caution"].iloc[0]
        assert ecb_row["relevance"] == "MACRO"

    def test_gold_keyword_beats_usd_keyword(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(GOLD_BEATS_USD_RSS)):
            collector = NewsCollector()
            df = collector.fetch_latest_news()
        assert df.iloc[0]["relevance"] == "GOLD_DIRECT"


class TestNewsCollectorEdgeCases:
    def test_missing_channel_returns_empty_df(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(NO_CHANNEL_RSS)):
            collector = NewsCollector()
            df = collector.fetch_latest_news()
        assert list(df.columns) == EXPECTED_COLUMNS
        assert len(df) == 0

    def test_network_error_returns_empty_df(self):
        from urllib.error import URLError
        with patch("urllib.request.urlopen", side_effect=URLError("connection refused")):
            collector = NewsCollector()
            df = collector.fetch_latest_news()
        assert list(df.columns) == EXPECTED_COLUMNS
        assert len(df) == 0

    def test_missing_fields_no_crash(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(MISSING_FIELDS_RSS)):
            collector = NewsCollector()
            df = collector.fetch_latest_news()
        assert list(df.columns) == EXPECTED_COLUMNS
        assert len(df) == 1
        row = df.iloc[0]
        assert row["title"] == ""
        assert row["description"] == ""
        assert row["url"] == ""

    def test_bad_pub_date_falls_back_to_now_utc(self):
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(BAD_DATE_RSS)):
            collector = NewsCollector()
            before = datetime.now(timezone.utc)
            df = collector.fetch_latest_news()
            after = datetime.now(timezone.utc)
        assert len(df) == 1
        ts = df.iloc[0]["timestamp"]
        assert ts.tzinfo is not None
        assert before <= ts <= after


class TestNewsCollectorSentimentToggle:
    def test_sentiment_zero_when_textblob_unavailable(self, monkeypatch):
        import data.news_collector as nc
        monkeypatch.setattr(nc, "TEXTBLOB_AVAILABLE", False)
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(CANNED_RSS)):
            collector = NewsCollector()
            df = collector.fetch_latest_news()
        for val in df["sentiment"]:
            assert val == 0.0, f"Expected 0.0 sentiment, got {val}"

    def test_init_warning_when_textblob_unavailable(self, monkeypatch, caplog):
        import data.news_collector as nc
        monkeypatch.setattr(nc, "TEXTBLOB_AVAILABLE", False)
        with caplog.at_level(logging.WARNING, logger="data.news_collector"):
            _ = NewsCollector()
        assert any("TextBlob" in rec.message for rec in caplog.records), (
            "Expected a TextBlob warning in logs, got: " + str(caplog.records)
        )
