# region imports
from AlgorithmImports import *
# endregion

from dataclasses import dataclass
from datetime import datetime, date

class CondorResearchConfig:
    price_vs_vwap_atr_bins = [-5, -1, -0.25, 0.25, 1, 5]
    bb_position_bins = [-np.inf, 0, 0.25, 0.75, 1.0, np.inf]
    gcp_pct_bins = [-np.inf, -0.01, -0.002, 0.002, 0.01, np.inf]
    adx_bins = [-np.inf,15,25,40,60,np.inf]
    time_bins = [-np.inf, 0, 30, 90, 180, 300, np.inf]
    time_bins_labels = [
        "premarket/neg",
        "0-30",
        "30-90",
        "90-180",
        "180-300",
        "300+"
    ]
    rsi_bins = [-np.inf, 30, 45, 55, 70, np.inf]
    vix_bins = [-np.inf, 15, 20, 25, np.inf]
    vix1d_bins = [-np.inf, "p30", "p70", np.inf]
    vix1d_percentiles = {
        "p30": 0.30,
        "p70": 0.70,
    }
    cushion_norm_bins = [-np.inf, -0.10, 0.0, 0.10, 0.25, 0.50, np.inf]
    cushion_norm_width_bins = [-np.inf, -0.05, 0.0, 0.05, 0.10, 0.20, np.inf]
    max_loss_norm_bins = [-np.inf, 2.0, 3.0, 4.0, 6.0, 8.0, np.inf]
    em_bins = [-np.inf, "p20", "p40", "p60", "p80", np.inf]
    em_percentiles = {
        "p20": 0.20,
        "p40": 0.40,
        "p60": 0.60,
        "p80": 0.80,
    }
    em_buffer: float = 1.10
