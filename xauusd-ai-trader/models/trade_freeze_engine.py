import pandas as pd
from typing import Any
import logging
from datetime import timedelta

from data.calendar_collector import CalendarCollector

logger = logging.getLogger(__name__)

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
            from features.price_features import compute_price_features
            from features.technical_features import compute_technical_features
            from features.structure_features import compute_structure_features
            X = df.copy()
            X = compute_price_features(X)
            X = compute_technical_features(X)
            X = compute_structure_features(X)
            X = X.dropna()
            
            if X.empty:
                return pd.Series(["WAIT"] * len(df), index=df.index)
                
            preds = self.predict(X)
            signals = pd.Series("WAIT", index=df.index)
            signals.loc[X.index] = preds
            
        # 2. Apply Freeze Logic
        frozen_signals = signals.copy()
        
        # Load calendar if not loaded
        if self.calendar_df.empty:
            collector = CalendarCollector()
            start = df["timestamp"].min()
            end = df["timestamp"].max()
            self.calendar_df = collector.get_events_in_range(start, end)
            
        if not self.calendar_df.empty:
            freeze_count = 0
            for idx, row in df.iterrows():
                bar_time = row["timestamp"]
                # Find events within ±freeze_minutes
                close_events = self.calendar_df[
                    (self.calendar_df["timestamp"] >= bar_time - timedelta(minutes=self.freeze_minutes)) &
                    (self.calendar_df["timestamp"] <= bar_time + timedelta(minutes=self.freeze_minutes))
                ]
                
                if not close_events.empty and frozen_signals.loc[idx] != "WAIT":
                    frozen_signals.loc[idx] = "WAIT"
                    freeze_count += 1
                    
            if freeze_count > 0:
                logger.info(f"{self.name}: Vetoed {freeze_count} signals due to High-Impact News proximity (±{self.freeze_minutes}m).")
                
        return frozen_signals
