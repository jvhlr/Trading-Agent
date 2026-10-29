import logging
from datetime import timedelta, timezone
from typing import Any, Optional
import numpy as np
import pandas as pd

from data.calendar_collector import CalendarCollector

logger = logging.getLogger(__name__)


def apply_freeze_veto(
    timestamps,
    predictions,
    freeze_minutes: int = 30,
    wait_label: int = 0,
    calendar_df: Optional[pd.DataFrame] = None,
):
    """
    Pure helper to apply economic calendar trade freeze veto to predictions.

    Flips any non-WAIT prediction (-1 SELL or +1 BUY) within ±freeze_minutes of a
    HIGH-impact economic calendar event (e.g. NFP, FOMC) to wait_label (default 0).

    Args:
        timestamps: Series, list, or ndarray of timestamps aligned to predictions.
        predictions: Array-like of integer signals (-1: SELL, 0: WAIT, +1: BUY).
        freeze_minutes: Proximity window in minutes (default 30).
        wait_label: Label representing WAIT (default 0).
        calendar_df: Optional pre-loaded calendar DataFrame. If None or empty,
                     loads events via CalendarCollector once covering the data range.

    Returns:
        Predictions matching the input type (list, ndarray, or pd.Series) with
        vetoed bars flipped to wait_label.
    """
    is_list = isinstance(predictions, list)
    is_series = isinstance(predictions, pd.Series)

    if len(predictions) == 0:
        if is_list:
            return []
        if is_series:
            return pd.Series([], dtype=predictions.dtype, index=predictions.index)
        return np.array([], dtype=int)

    if len(timestamps) != len(predictions):
        raise ValueError(
            f"Timestamps length ({len(timestamps)}) does not match predictions length ({len(predictions)})"
        )

    out_preds = np.array(predictions, copy=True)

    if freeze_minutes <= 0:
        if is_list:
            return out_preds.tolist()
        if is_series:
            return pd.Series(out_preds, index=predictions.index, name=predictions.name)
        return out_preds

    # Ensure timestamps are parsed and tz-aware UTC
    ts_series = pd.to_datetime(pd.Series(timestamps)).reset_index(drop=True)
    if ts_series.dt.tz is None:
        ts_utc = ts_series.dt.tz_localize(timezone.utc)
    else:
        ts_utc = ts_series.dt.tz_convert(timezone.utc)

    # Load calendar if not provided
    if calendar_df is None or calendar_df.empty:
        collector = CalendarCollector()
        start = ts_utc.min() - timedelta(minutes=freeze_minutes)
        end = ts_utc.max() + timedelta(minutes=freeze_minutes)
        calendar_df = collector.get_events_in_range(start, end)

    if calendar_df is None or calendar_df.empty:
        if is_list:
            return out_preds.tolist()
        if is_series:
            return pd.Series(out_preds, index=predictions.index, name=predictions.name)
        return out_preds

    if "impact" in calendar_df.columns:
        high_events = calendar_df[calendar_df["impact"].astype(str).str.upper() == "HIGH"]
    else:
        high_events = calendar_df

    if high_events.empty:
        if is_list:
            return out_preds.tolist()
        if is_series:
            return pd.Series(out_preds, index=predictions.index, name=predictions.name)
        return out_preds

    ev_times = pd.to_datetime(high_events["timestamp"])
    if ev_times.dt.tz is None:
        ev_utc = ev_times.dt.tz_localize(timezone.utc)
    else:
        ev_utc = ev_times.dt.tz_convert(timezone.utc)

    window = timedelta(minutes=freeze_minutes)
    veto_mask = np.zeros(len(ts_utc), dtype=bool)

    for ev_time in ev_utc:
        in_window = (ts_utc >= ev_time - window) & (ts_utc <= ev_time + window)
        veto_mask |= in_window.values

    # Flip non-WAIT predictions to wait_label
    flip_mask = veto_mask & (out_preds != wait_label)
    out_preds[flip_mask] = wait_label

    if is_list:
        return out_preds.tolist()
    if is_series:
        return pd.Series(out_preds, index=predictions.index, name=predictions.name)
    return out_preds


class TradeFreezeEngine:
    """
    Acts as a veto wrapper around any underlying classifier.
    If the current bar timestamp is within freeze_minutes of a High Impact
    Economic Calendar event (e.g., NFP, FOMC), it overrides the model's signal
    to 'WAIT'.
    """

    def __init__(self, base_model: Any, freeze_minutes: int = 30):
        self.base_model = base_model
        self.freeze_minutes = freeze_minutes
        self.calendar_df = pd.DataFrame()
        self.name = f"Freeze-Protected {getattr(base_model, 'name', base_model.__class__.__name__)}"

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series):
        """Pass-through to underlying model."""
        if hasattr(self.base_model, "fit"):
            self.base_model.fit(X_train, y_train)

    def predict(self, X: pd.DataFrame) -> pd.Series:
        """Pass-through to underlying model."""
        return self.base_model.predict(X)

    def get_signals(self, df: pd.DataFrame) -> pd.Series:
        """
        Generate signals from the base model, then apply the Trade Freeze overlay.
        """
        if df.empty:
            return pd.Series(dtype=str)

        # 1. Get base signals
        if hasattr(self.base_model, "get_signals"):
            signals = self.base_model.get_signals(df)
        else:
            # Recreate features if get_signals is not natively supported
            from features.price_features import add_all_price_features
            from features.technical_features import add_all_technical_features
            from features.structure_features import add_all_structure_features

            X = df.copy()
            X = add_all_price_features(X)
            X = add_all_technical_features(X)
            X = add_all_structure_features(X)
            X = X.dropna()

            if X.empty:
                return pd.Series(["WAIT"] * len(df), index=df.index)

            preds = self.predict(X)
            signals = pd.Series("WAIT", index=df.index)
            signals.loc[X.index] = preds

        # 2. Apply Freeze Logic via shared helper
        str_to_int = {"BUY": 1, "SELL": -1, "WAIT": 0}
        int_to_str = {1: "BUY", -1: "SELL", 0: "WAIT"}

        int_preds = [str_to_int.get(s, 0) if isinstance(s, str) else int(s) for s in signals]

        if self.calendar_df.empty and not df.empty:
            collector = CalendarCollector()
            start = df["timestamp"].min() - timedelta(minutes=self.freeze_minutes)
            end = df["timestamp"].max() + timedelta(minutes=self.freeze_minutes)
            self.calendar_df = collector.get_events_in_range(start, end)

        vetoed_int = apply_freeze_veto(
            timestamps=df["timestamp"],
            predictions=int_preds,
            freeze_minutes=self.freeze_minutes,
            wait_label=0,
            calendar_df=self.calendar_df,
        )

        frozen_signals = pd.Series(
            [int_to_str.get(v, "WAIT") for v in vetoed_int],
            index=df.index,
        )

        freeze_count = (signals != frozen_signals).sum()
        if freeze_count > 0:
            logger.info(
                f"{self.name}: Vetoed {freeze_count} signals due to High-Impact News proximity (±{self.freeze_minutes}m)."
            )

        return frozen_signals
