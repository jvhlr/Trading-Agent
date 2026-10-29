"""
Tests -- CalendarCollector (Phase 5)

Pins the deterministic rules of data/calendar_collector.py:
  - NFP = first Friday of the month at 13:30 UTC
  - FOMC = 3rd Wednesday of even-numbered months at 18:00 UTC
  - Schema: [timestamp, event, impact, currency, description], UTC-aware
  - Events sorted ascending; full 2025 year yields exactly 18 events
  - Boundary inclusivity, empty-range, naive-datetime, and determinism
"""

import sys
from pathlib import Path
import pytest
import pandas as pd
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from data.calendar_collector import CalendarCollector


def _utc(*args):
    return datetime(*args, tzinfo=timezone.utc)


EXPECTED_COLUMNS = ["timestamp", "event", "impact", "currency", "description"]


class TestCalendarCollectorSchema:
    def test_empty_range_returns_correct_columns(self):
        collector = CalendarCollector()
        start = _utc(2025, 1, 5)
        end = _utc(2025, 1, 5, 23, 59)
        df = collector.get_events_in_range(start, end)
        assert list(df.columns) == EXPECTED_COLUMNS
        assert len(df) == 0

    def test_non_empty_result_has_correct_columns(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 1, 1), _utc(2025, 1, 31))
        assert list(df.columns) == EXPECTED_COLUMNS

    def test_timestamps_are_tz_aware_utc(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 1, 1), _utc(2025, 6, 30))
        for ts in df["timestamp"]:
            assert ts.tzinfo is not None
            assert ts.utcoffset() == timedelta(0)


class TestCalendarCollectorNFP:
    def test_january_2025_nfp_anchor(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 1, 1), _utc(2025, 1, 31))
        nfp = df[df["event"] == "Non Farm Payrolls"]
        assert len(nfp) == 1
        ts = nfp.iloc[0]["timestamp"]
        assert ts == _utc(2025, 1, 3, 13, 30)

    def test_nfp_time_is_13_30_utc(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 1, 1), _utc(2025, 12, 31))
        nfp = df[df["event"] == "Non Farm Payrolls"]
        for _, row in nfp.iterrows():
            ts = row["timestamp"]
            assert ts.hour == 13 and ts.minute == 30

    def test_nfp_first_friday_rule(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 1, 1), _utc(2025, 12, 31))
        nfp = df[df["event"] == "Non Farm Payrolls"]
        for _, row in nfp.iterrows():
            ts = row["timestamp"]
            assert ts.weekday() == 4
            assert ts.day <= 7

    def test_full_year_2025_has_12_nfp(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 1, 1), _utc(2025, 12, 31))
        nfp = df[df["event"] == "Non Farm Payrolls"]
        assert len(nfp) == 12

    def test_nfp_impact_and_currency(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 1, 1), _utc(2025, 1, 31))
        nfp = df[df["event"] == "Non Farm Payrolls"]
        row = nfp.iloc[0]
        assert row["impact"] == "HIGH"
        assert row["currency"] == "USD"
        assert isinstance(row["description"], str) and len(row["description"]) > 0


class TestCalendarCollectorFOMC:
    def test_february_2025_fomc_anchor(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 2, 1), _utc(2025, 2, 28))
        fomc = df[df["event"] == "FOMC Statement & Rate Decision"]
        assert len(fomc) == 1
        ts = fomc.iloc[0]["timestamp"]
        assert ts == _utc(2025, 2, 19, 18, 0)

    def test_march_2025_is_odd_no_fomc(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 3, 1), _utc(2025, 3, 31))
        fomc = df[df["event"] == "FOMC Statement & Rate Decision"]
        assert len(fomc) == 0

    def test_fomc_only_in_even_months(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 1, 1), _utc(2025, 12, 31))
        fomc = df[df["event"] == "FOMC Statement & Rate Decision"]
        for _, row in fomc.iterrows():
            ts = row["timestamp"]
            assert ts.month % 2 == 0

    def test_fomc_third_wednesday_rule(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 1, 1), _utc(2025, 12, 31))
        fomc = df[df["event"] == "FOMC Statement & Rate Decision"]
        for _, row in fomc.iterrows():
            ts = row["timestamp"]
            assert ts.weekday() == 2
            assert 15 <= ts.day <= 21

    def test_fomc_time_is_18_00_utc(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 1, 1), _utc(2025, 12, 31))
        fomc = df[df["event"] == "FOMC Statement & Rate Decision"]
        for _, row in fomc.iterrows():
            ts = row["timestamp"]
            assert ts.hour == 18 and ts.minute == 0

    def test_full_year_2025_has_6_fomc(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 1, 1), _utc(2025, 12, 31))
        fomc = df[df["event"] == "FOMC Statement & Rate Decision"]
        assert len(fomc) == 6


class TestCalendarCollectorFullYear:
    def test_full_year_2025_total_count(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 1, 1), _utc(2025, 12, 31))
        assert len(df) == 18

    def test_events_sorted_ascending(self):
        collector = CalendarCollector()
        df = collector.get_events_in_range(_utc(2025, 1, 1), _utc(2025, 12, 31))
        timestamps = list(df["timestamp"])
        assert timestamps == sorted(timestamps)


class TestCalendarCollectorBoundary:
    def test_event_exactly_on_start_boundary_is_included(self):
        collector = CalendarCollector()
        start = _utc(2025, 1, 3, 13, 30)
        end = _utc(2025, 1, 31, 23, 59)
        df = collector.get_events_in_range(start, end)
        nfp = df[df["event"] == "Non Farm Payrolls"]
        assert len(nfp) >= 1
        assert nfp.iloc[0]["timestamp"] == start

    def test_event_exactly_on_end_boundary_is_included(self):
        collector = CalendarCollector()
        start = _utc(2025, 1, 1)
        end = _utc(2025, 1, 3, 13, 30)
        df = collector.get_events_in_range(start, end)
        nfp = df[df["event"] == "Non Farm Payrolls"]
        assert len(nfp) == 1

    def test_single_day_no_events(self):
        collector = CalendarCollector()
        start = _utc(2025, 1, 6, 0, 0)
        end = _utc(2025, 1, 6, 23, 59)
        df = collector.get_events_in_range(start, end)
        assert list(df.columns) == EXPECTED_COLUMNS
        assert len(df) == 0


class TestCalendarCollectorNaiveDatetime:
    def test_naive_start_treated_as_utc(self):
        collector = CalendarCollector()
        naive_start = datetime(2025, 1, 1)
        naive_end = datetime(2025, 1, 31)
        aware_start = _utc(2025, 1, 1)
        aware_end = _utc(2025, 1, 31)
        df_naive = collector.get_events_in_range(naive_start, naive_end)
        df_aware = collector.get_events_in_range(aware_start, aware_end)
        assert len(df_naive) == len(df_aware)
        for ts in df_naive["timestamp"]:
            assert ts.tzinfo is not None


class TestCalendarCollectorDeterminism:
    def test_same_range_is_deterministic(self):
        collector = CalendarCollector()
        start = _utc(2025, 1, 1)
        end = _utc(2025, 12, 31)
        df1 = collector.get_events_in_range(start, end)
        df2 = collector.get_events_in_range(start, end)
        pd.testing.assert_frame_equal(df1, df2)
