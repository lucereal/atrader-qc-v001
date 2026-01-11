# region imports
from AlgorithmImports import *
# endregion
import numpy as np
import pandas as pd

def expectancy(x, *, zero_is_loss: bool = False, eps: float = 0.0, return_parts: bool = False):
    """
    Compute expectancy from a 1D series/array of P&L values.

    Params:
      zero_is_loss:
        - False: treat pnl == 0 as neutral (excluded from win/loss averages, but still counts in total)
        - True:  treat pnl == 0 as loss (your original behavior was close to this)
      eps:
        Floating tolerance: treat |pnl| <= eps as zero.
      return_parts:
        If True, returns a dict with win_rate, avg_win, avg_loss, expectancy.
        If False, returns expectancy only.
    """
    x = pd.Series(x).dropna()

    if len(x) == 0:
        out = {"win_rate": np.nan, "avg_win": np.nan, "avg_loss": np.nan, "expectancy": np.nan}
        return out if return_parts else np.nan

    # Define win/loss with optional epsilon + zero handling
    is_win = x > eps
    if zero_is_loss:
        is_loss = ~is_win          # includes zeros
    else:
        is_loss = x < -eps         # excludes zeros
        # zeros are neither win nor loss (neutral)

    win_rate = is_win.mean()       # still over total count (including zeros)

    avg_win = x[is_win].mean() if is_win.any() else np.nan
    avg_loss = x[is_loss].mean() if is_loss.any() else np.nan

    exp = win_rate * avg_win + (1 - win_rate) * avg_loss

    out = {"win_rate": float(win_rate), "avg_win": avg_win, "avg_loss": avg_loss, "expectancy": exp}
    return out if return_parts else exp
