# region imports
from AlgorithmImports import *
# endregion

def get_latest_trade_analytics_key(object_store):
    keys = object_store.Keys

    # keep only trade analytics files
    analytics_keys = [
        k for k in keys if k.endswith("_trade_analytics.json")
    ]

    if not analytics_keys:
        return None

    # ISO timestamp makes lexicographic sort correct
    return sorted(analytics_keys)[-1]
    
def expectancy(x):
    win_rate = (x > 0).mean()
    avg_win = x[x > 0].mean()
    avg_loss = x[x <= 0].mean()
    return win_rate * avg_win + (1 - win_rate) * avg_loss

# x here is a pandas series - a 1-dimensional seq of nums
def expectancy_v2(x):
    x = pd.Series(x).dropna()
    if len(x) == 0:
        return np.nan

    win_rate = (x > 0).mean()
    avg_win = x[x > 0].mean() if (x > 0).any() else np.nan
    avg_loss = x[x <= 0].mean() if (x <= 0).any() else np.nan
    return win_rate * avg_win + (1 - win_rate) * avg_loss
