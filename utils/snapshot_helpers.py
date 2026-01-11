from datetime import datetime, time, timedelta
import pytz

def minutes_since_open(
    ts: datetime,
    market_tz=pytz.timezone("US/Eastern"),
    open_time=time(9, 30)
) -> int:
    """
    Minutes since market open.
    ts must be timezone-aware.
    """
    if ts.tzinfo is None:
        raise ValueError("ts must be timezone-aware")

    ts_local = ts.astimezone(market_tz)
    open_dt = market_tz.localize(
        datetime.combine(ts_local.date(), open_time)
    )

    delta = ts_local - open_dt
    return int(delta.total_seconds() // 60)

def minutes_since_entry(entry_ts: datetime, now_ts: datetime) -> int:
    """
    Minutes since trade entry.
    Both datetimes must be timezone-aware.
    """
    if entry_ts.tzinfo is None or now_ts.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")

    delta = now_ts - entry_ts
    return int(delta.total_seconds() // 60)

def horizon_min(mse: int, step: int = 15) -> int:
    """
    Snap minutes_since_entry to nearest horizon bucket.
    Example: 14 → 15, 16 → 15, 29 → 30
    """
    return int(round(mse / step) * step)
