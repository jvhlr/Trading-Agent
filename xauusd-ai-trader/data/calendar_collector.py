import logging
import pandas as pd
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class CalendarCollector:
    """
    Generates deterministic Economic Calendar events for Offline Research Backtesting.
    Simulates high-impact events like NFP (Non-Farm Payroll) and FOMC accurately
    mapped to historical dates to test the Trade Freeze Engine.
    """
    
    def __init__(self):
        pass
        
    def get_events_in_range(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Generates a DataFrame of synthetic high-impact events between start_date and end_date.
        
        Args:
            start_date: Start datetime (UTC)
            end_date: End datetime (UTC)
            
        Returns:
            DataFrame with columns: [timestamp, event, impact, currency, description]
        """
        events = []
        
        # Ensure UTC
        if start_date.tzinfo is None:
            start_date = start_date.replace(tzinfo=timezone.utc)
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
            
        current = start_date
        
        # We will generate synthetic NFP events (First Friday of the month at 12:30 UTC or 13:30 UTC depending on DST)
        # We will also generate synthetic FOMC events (Approx every 6 weeks on Wednesday 18:00 UTC)
        
        while current <= end_date:
            # Check for NFP (First Friday of the month)
            if current.weekday() == 4 and current.day <= 7:
                # Typically released at 13:30 UTC (EST 08:30)
                event_time = current.replace(hour=13, minute=30, second=0, microsecond=0)
                if start_date <= event_time <= end_date:
                    events.append({
                        "timestamp": event_time,
                        "event": "Non Farm Payrolls",
                        "impact": "HIGH",
                        "currency": "USD",
                        "description": "Measures the change in the number of employed people during the previous month, excluding the farming industry."
                    })
                    
            # Check for FOMC (Roughly 3rd Wednesday of every other month)
            if current.weekday() == 2 and 15 <= current.day <= 21 and current.month % 2 == 0:
                # Typically released at 18:00 UTC or 19:00 UTC
                event_time = current.replace(hour=18, minute=0, second=0, microsecond=0)
                if start_date <= event_time <= end_date:
                    events.append({
                        "timestamp": event_time,
                        "event": "FOMC Statement & Rate Decision",
                        "impact": "HIGH",
                        "currency": "USD",
                        "description": "Federal Open Market Committee statement and interest rate decision."
                    })
                    
            current += timedelta(days=1)
            
        if not events:
            return pd.DataFrame(columns=["timestamp", "event", "impact", "currency", "description"])
            
        df = pd.DataFrame(events)
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df

if __name__ == "__main__":
    collector = CalendarCollector()
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2025, 12, 31, tzinfo=timezone.utc)
    df = collector.get_events_in_range(start, end)
    print(df.head(10))
