# region imports
from AlgorithmImports import *
# endregion
from dataclasses import dataclass
from QuantConnect import Resolution, Scheduling
from datetime import datetime, date

@dataclass
class AlgorithmConfig:
    """QuantConnect/Backtest environment settings"""
    start_date: datetime = datetime(2024, 8, 30)
    end_date: datetime = datetime(2024, 10, 1)
    initial_cash: float = 100000
    benchmark: str = "SPY"
    resolution: Resolution = Resolution.MINUTE  # or DAILY, HOUR
    data_normalization: DataNormalizationMode = DataNormalizationMode.RAW
    symbol = 'SPY'
    scheduling_minutes = 5
    scheduling_date_rule = "every_day"


@dataclass
class ShortIronCondorConfig:

    start_trading_hour = 10
    start_trading_minute = 00

    symbol: str = 'SPY'
    # Entry Parameters
    days_to_expiration: int = 0
    dte_range: tuple[int,int] = (0,7)
    short_call_delta_range: tuple[float, float] = (0.15, 0.25)
    short_put_delta_range: tuple[float, float] = (-0.25, -0.15) 
    call_spread_width: int = 5
    put_spread_width: int = 5
    spread_width_range: tuple[int, int] = (2,10)
    
    # Position Management
    position_size: int = 1  # contracts per trade
    max_positions: int = 5
    
    # Risk Parameters
    max_loss_per_trade: float = 500
    max_portfolio_loss: float = 5000
    profit_target_percent: float = 0.5 * 100  # Close at 50% profit
    max_loss_percent: float = -0.5 * 100 # Close at 20% profit 
    close_at_hour: int = 13
    
    # Symbols to trade
    symbols: list = None
    
    def __post_init__(self):
        if self.symbols is None:
            self.symbols = ["SPY"]


@dataclass(frozen=True)
class ContractSelectionConfig:
    dte_range: tuple[int, int]
    short_call_delta_range: tuple[float, float]
    short_put_delta_range: tuple[float, float]
    spread_width_range: tuple[float, float]

@dataclass(frozen=True)
class IronCondorScoringConfig:
    min_vertical_credit: float = 0.05
    min_credit_ratio: float = 0.15
    top_n_per_side: int = 25

    em_buffer: float = 1.0
    require_em_ok: bool = True
    min_rr: float = 0.12

    missing_delta_score: float = 0.5

    # weights
    w_rr: float = 2.0
    w_cushion: float = 1.0
    w_center: float = 0.5
    w_balance: float = 0.5
    w_credit: float = 0.2
    
@dataclass
class TradeDayFilterConfig:
    is_check_macro_event: bool = False
    is_check_overnight_gap: bool = False
    is_check_vwap_threshold: bool = False
    is_check_bb_threshold: bool = False
    is_check_rsi_threshold: bool = False
    is_check_adx_threshold: bool = False
    is_check_vix_threshold: bool = False
    is_check_vix1d_threshold: bool = False

    overnight_gap_atr_threshold: float = 0.4  # Gap as % of ATR
    vwap_atr_multiplier: float = 0.5  # Distance from VWAP as multiple of ATR
    bb_normalized_distance_threshold: float = 0.7  # 0.6=conservative, 0.65=balanced, 0.7=permissive
    rsi_oversold_threshold: float = 20.0  # RSI below this = oversold
    rsi_overbought_threshold: float = 80.0  # RSI above this = overbought
    adx_trend_threshold: float = 22.0  # ADX above this = strong trend (skip trading)
    vix_threshold: float = 30.0
    vix1d_threshold: float = 25.0

    MACRO_EVENTS = {
        date(2024, 1, 5),
        date(2024, 1, 11),
        date(2024, 1, 12),
        date(2024, 1, 17),
        date(2024, 1, 26),

        date(2024, 2, 2),
        date(2024, 2, 4),
        date(2024, 2, 13),
        date(2024, 2, 15),
        date(2024, 2, 16),
        date(2024, 2, 29),

        date(2024, 3, 6),
        date(2024, 3, 7),
        date(2024, 3, 8),
        date(2024, 3, 12),
        date(2024, 3, 14),
        date(2024, 3, 20),
        date(2024, 3, 22),
        date(2024, 3, 27),
        date(2024, 3, 29),

        date(2024, 4, 3),
        date(2024, 4, 5),
        date(2024, 4, 10),
        date(2024, 4, 11),
        date(2024, 4, 15),
        date(2024, 4, 16),
        date(2024, 4, 26),

        date(2024, 5, 1),
        date(2024, 5, 3),
        date(2024, 5, 14),
        date(2024, 5, 15),
        date(2024, 5, 22),
        date(2024, 5, 31),

        date(2024, 6, 12),
        date(2024, 6, 13),
        date(2024, 6, 18),
        date(2024, 6, 28),

        date(2024, 7, 2),
        date(2024, 7, 5),
        date(2024, 7, 9),
        date(2024, 7, 10),
        date(2024, 7, 11),
        date(2024, 7, 12),
        date(2024, 7, 15),
        date(2024, 7, 16),
        date(2024, 7, 26),
        date(2024, 7, 31),

        date(2024, 8, 2),
        date(2024, 8, 13),
        date(2024, 8, 14),
        date(2024, 8, 15),
        date(2024, 8, 23),
        date(2024, 8, 30),

        date(2024, 9, 6),
        date(2024, 9, 11),
        date(2024, 9, 12),
        date(2024, 9, 18),
        date(2024, 9, 26),
        date(2024, 9, 27),
        date(2024, 9, 30),

        date(2024, 10, 10),
        date(2024, 10, 11),
        date(2024, 10, 17),
        date(2024, 10, 31),

        date(2024, 11, 1),
        date(2024, 11, 7),
        date(2024, 11, 13),
        date(2024, 11, 14),
        date(2024, 11, 15),
        date(2024, 11, 27),

        date(2024, 12, 4),
        date(2024, 12, 6),
        date(2024, 12, 11),
        date(2024, 12, 12),
        date(2024, 12, 17),
        date(2024, 12, 18),
        date(2024, 12, 20),

    }

