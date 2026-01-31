# region imports
from AlgorithmImports import *
# endregion
from datetime import datetime, time, timedelta
import pytz

def minutes_since_open(
    ts: datetime,
    open_time=time(9, 30)
) -> int:
    open_dt = datetime.combine(ts.date(), open_time)
    return int((ts - open_dt).total_seconds() // 60)

def minutes_since_entry(entry_ts: datetime, now_ts: datetime) -> int:

    delta = now_ts - entry_ts
    return int(delta.total_seconds() // 60)

def horizon_min(mse: int, step: int = 15) -> int:
    """
    Snap minutes_since_entry to nearest horizon bucket.
    Example: 14 → 15, 16 → 15, 29 → 30
    """
    return int(round(mse / step) * step)
