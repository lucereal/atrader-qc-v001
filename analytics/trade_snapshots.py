# region imports
from utils.snapshot_helpers import (
    minutes_since_open,
    minutes_since_entry,
    horizon_min
)
# endregion
class TradeSnapshots:
    def __init__(self):
        self.trade_snapshots = []
    
    def add_snapshot(
        self,
        trade_id: str,
        now_time,
        trade_entry_time,
        spot: float,
        pnl_mid: float,
        pnl_norm: float,
        close_mid: float,
        close_bid: float,
        close_ask: float,
    ):
        msmo = minutes_since_open(now_time)
        mse = minutes_since_entry(trade_entry_time, now_time)
        h = horizon_min(mse)
        now_time_str = now_time.strftime("%Y-%m-%d, %H:%M:%S")
        self.trade_snapshots.append({
            "trade_id": trade_id,
            "ts": now_time_str,
            "minutes_since_market_open": msmo,
            "minutes_since_entry": mse,
            "horizon_min": h,
            "underlying": spot,
            "pnl_mid": pnl_mid,
            "pnl_norm": pnl_norm,
            "close_mid": close_mid,
            "close_ask": close_ask,
            "close_bid": close_bid
        })
