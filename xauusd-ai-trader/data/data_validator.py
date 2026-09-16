"""
XAUUSD AI Trading Research System — Data Validator

Validates dataset quality before it enters the research pipeline.
Checks for duplicates, missing candles, invalid OHLC, impossible values,
timestamp problems, and abnormal spreads.

If the overall verdict is FAIL, phase progression should be BLOCKED.
Fix the data first.
"""

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from enum import Enum
from typing import Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Severity of a validation issue."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Verdict(Enum):
    """Overall dataset quality verdict."""
    GOOD = "GOOD"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass
class ValidationCheck:
    """Result of a single validation check."""
    name: str
    passed: bool
    severity: Severity
    count: int = 0  # Number of issues found
    details: str = ""

    def __str__(self) -> str:
        status = "PASS" if self.passed else f"FAIL ({self.severity.value})"
        detail = f" — {self.details}" if self.details else ""
        count_str = f" [{self.count} issue(s)]" if self.count > 0 else ""
        return f"  [{status}] {self.name}{count_str}{detail}"


@dataclass
class DataQualityReport:
    """
    Complete data quality report.

    Contains results for each check, overall verdict, and metadata.
    If verdict is FAIL, the dataset should NOT proceed to feature
    engineering or modeling.
    """
    symbol: str = ""
    broker_symbol: str = ""
    timeframe: str = ""
    row_count: int = 0
    date_range: str = ""
    checks: list[ValidationCheck] = field(default_factory=list)
    verdict: Verdict = Verdict.GOOD

    def add_check(self, check: ValidationCheck) -> None:
        """Add a check result and update the overall verdict."""
        self.checks.append(check)
        if not check.passed:
            if check.severity == Severity.CRITICAL:
                self.verdict = Verdict.FAIL
            elif check.severity == Severity.WARNING and self.verdict != Verdict.FAIL:
                self.verdict = Verdict.WARNING

    def __str__(self) -> str:
        lines = [
            "=" * 60,
            "DATASET QUALITY REPORT",
            "=" * 60,
            f"  Symbol:         {self.symbol}",
            f"  Broker Symbol:  {self.broker_symbol}",
            f"  Timeframe:      {self.timeframe}",
            f"  Rows:           {self.row_count}",
            f"  Period:         {self.date_range}",
            "",
            "  Checks:",
        ]
        for check in self.checks:
            lines.append(str(check))
        lines.extend([
            "",
            f"  VERDICT: {self.verdict.value}",
            "=" * 60,
        ])
        return "\n".join(lines)


# ── Timeframe → expected interval mapping ────────────────────────────────────
TIMEFRAME_INTERVALS = {
    "M1": timedelta(minutes=1),
    "M5": timedelta(minutes=5),
    "M15": timedelta(minutes=15),
    "M30": timedelta(minutes=30),
    "H1": timedelta(hours=1),
    "H4": timedelta(hours=4),
    "D1": timedelta(days=1),
    "W1": timedelta(weeks=1),
}


def validate(
    df: pd.DataFrame,
    timeframe: str,
    symbol: str = "XAUUSD",
    broker_symbol: str = "",
    max_missing_pct: float = 5.0,
    max_duplicates: int = 0,
    max_spread_multiplier: float = 10.0,
    min_price: float = 100.0,
    max_price: float = 50000.0,
) -> DataQualityReport:
    """
    Validate a dataset and produce a quality report.

    Args:
        df: DataFrame with columns: timestamp, open, high, low, close,
            and optionally: tick_volume, spread, real_volume.
        timeframe: Timeframe string (e.g., 'H1').
        symbol: Internal symbol name.
        broker_symbol: Broker's symbol name.
        max_missing_pct: Maximum allowable % of missing candles.
        max_duplicates: Maximum allowable duplicate timestamps.
        max_spread_multiplier: Flag spreads > this * median.
        min_price: Minimum plausible price.
        max_price: Maximum plausible price.

    Returns:
        DataQualityReport with all check results and overall verdict.
    """
    report = DataQualityReport(
        symbol=symbol,
        broker_symbol=broker_symbol,
        timeframe=timeframe,
        row_count=len(df),
    )

    if len(df) == 0:
        report.add_check(ValidationCheck(
            name="Non-empty dataset",
            passed=False,
            severity=Severity.CRITICAL,
            details="Dataset is empty.",
        ))
        return report

    # Ensure timestamp column exists
    if "timestamp" not in df.columns:
        report.add_check(ValidationCheck(
            name="Timestamp column exists",
            passed=False,
            severity=Severity.CRITICAL,
            details="Missing 'timestamp' column.",
        ))
        return report

    # Record date range
    ts = df["timestamp"]
    report.date_range = f"{ts.min()} -> {ts.max()}"

    # ── Check 1: Duplicate timestamps ────────────────────────────────────
    dup_count = int(ts.duplicated().sum())
    report.add_check(ValidationCheck(
        name="No duplicate timestamps",
        passed=dup_count <= max_duplicates,
        severity=Severity.CRITICAL if dup_count > max_duplicates else Severity.INFO,
        count=dup_count,
        details=f"{dup_count} duplicate(s) found" if dup_count > 0 else "",
    ))

    # ── Check 2: Missing candles ─────────────────────────────────────────
    interval = TIMEFRAME_INTERVALS.get(timeframe)
    if interval is not None and len(df) > 1:
        # Calculate expected vs actual candle count
        # Note: we skip weekends for intraday timeframes
        total_span = ts.max() - ts.min()
        if timeframe not in ("D1", "W1"):
            # Gold/Forex market trades ~23 hours per business day (1h daily rollover break)
            date_range = pd.bdate_range(ts.min(), ts.max())
            expected_per_day = timedelta(hours=23) / interval
            expected_count = int(len(date_range) * expected_per_day)
        else:
            expected_count = int(total_span / interval) + 1

        # Avoid division by zero
        if expected_count > 0:
            actual_count = len(df)
            missing_count = max(0, expected_count - actual_count)
            missing_pct = (missing_count / expected_count) * 100

            report.add_check(ValidationCheck(
                name="Missing candles within threshold",
                passed=missing_pct <= max_missing_pct,
                severity=Severity.WARNING if missing_pct <= max_missing_pct * 3 else Severity.CRITICAL,
                count=missing_count,
                details=f"{missing_pct:.1f}% missing (expected ~{expected_count}, got {actual_count})",
            ))
        else:
            report.add_check(ValidationCheck(
                name="Missing candles within threshold",
                passed=True,
                severity=Severity.INFO,
                details="Cannot estimate expected count.",
            ))
    else:
        report.add_check(ValidationCheck(
            name="Missing candles within threshold",
            passed=True,
            severity=Severity.INFO,
            details=f"Unknown interval for timeframe '{timeframe}' or insufficient data.",
        ))

    # ── Check 3: Timestamp ordering ──────────────────────────────────────
    is_sorted = ts.is_monotonic_increasing
    report.add_check(ValidationCheck(
        name="Timestamps monotonically increasing",
        passed=is_sorted,
        severity=Severity.CRITICAL,
        details="" if is_sorted else "Timestamps are not in order.",
    ))

    # ── Check 4: Invalid OHLC relationships ──────────────────────────────
    ohlc_cols = ["open", "high", "low", "close"]
    if all(c in df.columns for c in ohlc_cols):
        # High must be >= Open, Close, Low
        # Low must be <= Open, Close, High
        invalid_high = (df["high"] < df["open"]) | (df["high"] < df["close"])
        invalid_low = (df["low"] > df["open"]) | (df["low"] > df["close"])
        invalid_hl = df["high"] < df["low"]
        invalid_ohlc = invalid_high | invalid_low | invalid_hl
        invalid_count = int(invalid_ohlc.sum())

        report.add_check(ValidationCheck(
            name="Valid OHLC relationships",
            passed=invalid_count == 0,
            severity=Severity.CRITICAL if invalid_count > 0 else Severity.INFO,
            count=invalid_count,
            details=f"{invalid_count} candle(s) with invalid OHLC" if invalid_count > 0 else "",
        ))

        # ── Check 5: Price range sanity ──────────────────────────────────
        all_prices = pd.concat([df["open"], df["high"], df["low"], df["close"]])
        below_min = int((all_prices < min_price).sum())
        above_max = int((all_prices > max_price).sum())
        negative = int((all_prices < 0).sum())
        impossible_count = below_min + above_max + negative

        details_parts = []
        if negative > 0:
            details_parts.append(f"{negative} negative")
        if below_min > 0:
            details_parts.append(f"{below_min} below ${min_price}")
        if above_max > 0:
            details_parts.append(f"{above_max} above ${max_price}")

        report.add_check(ValidationCheck(
            name="Price values within plausible range",
            passed=impossible_count == 0,
            severity=Severity.CRITICAL if negative > 0 else Severity.WARNING,
            count=impossible_count,
            details=", ".join(details_parts) if details_parts else "",
        ))
    else:
        report.add_check(ValidationCheck(
            name="OHLC columns present",
            passed=False,
            severity=Severity.CRITICAL,
            details=f"Missing OHLC columns. Found: {list(df.columns)}",
        ))

    # ── Check 6: Abnormal spreads ────────────────────────────────────────
    if "spread" in df.columns:
        spreads = df["spread"]
        if spreads.median() > 0:
            abnormal_spread = spreads > (spreads.median() * max_spread_multiplier)
            abnormal_count = int(abnormal_spread.sum())
            report.add_check(ValidationCheck(
                name="Spread values within normal range",
                passed=abnormal_count == 0,
                severity=Severity.WARNING,
                count=abnormal_count,
                details=(
                    f"{abnormal_count} candle(s) with spread > {max_spread_multiplier}x median "
                    f"(median={spreads.median():.0f}, max={spreads.max():.0f})"
                    if abnormal_count > 0 else
                    f"Median spread: {spreads.median():.0f}"
                ),
            ))
        else:
            report.add_check(ValidationCheck(
                name="Spread values within normal range",
                passed=True,
                severity=Severity.INFO,
                details="Spread median is 0 — field may not be populated.",
            ))
    else:
        report.add_check(ValidationCheck(
            name="Spread availability",
            passed=True,
            severity=Severity.INFO,
            details="Spread column not present — recorded as unavailable.",
        ))

    # ── Check 7: Timezone verification ───────────────────────────────────
    if hasattr(ts.dtype, "tz") and ts.dtype.tz is not None:
        tz_str = str(ts.dtype.tz)
        is_utc = tz_str in ("UTC", "utc", "timezone.utc")
        report.add_check(ValidationCheck(
            name="Timestamps are UTC",
            passed=is_utc,
            severity=Severity.WARNING if not is_utc else Severity.INFO,
            details=f"Timezone: {tz_str}" + ("" if is_utc else " — expected UTC"),
        ))
    else:
        report.add_check(ValidationCheck(
            name="Timestamps are UTC",
            passed=False,
            severity=Severity.WARNING,
            details="Timestamps are timezone-naive. Should be UTC-aware.",
        ))

    # Log the report
    logger.info("\n%s", report)

    return report
