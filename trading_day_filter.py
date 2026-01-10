# region imports
from AlgorithmImports import *
from config import TradeDayFilterConfig
# endregion

class DayTradeFilter:
    def __init__(self, name, check_method, params_builder, threshold_values):
        self.name = name
        self.check_method = check_method
        self.params_builder = params_builder
        self.threshold_values = threshold_values
    
    def should_skip_trading(self, params):
        args = self.params_builder(**vars(params))
        args.extend(self.threshold_values.values())
        return self.check_method(*args)
    
    def to_dict(self, params):
        """Return all input and threshold values for logging"""
        return {
            'name': self.name,
            'input_values': vars(params),
            'threshold_values': self.threshold_values
        }
    
class FilteringParams:
    def __init__(self, filter_data):
        self.current_date = filter_data['current_date']
        self.current_open = filter_data['current_open']
        self.prev_day_close = filter_data['prev_day_close']
        self.current_atr = filter_data['current_atr']
        self.current_price = filter_data['current_price']
        self.current_vwap = filter_data['current_vwap']
        self.current_bb = filter_data['current_bb']
        self.current_rsi = filter_data['current_rsi']
        self.current_adx = filter_data['current_adx']
        self.current_vix = filter_data['current_vix']
        self.current_vix1d = filter_data['current_vix1d']

class FilterCheckResult:
    def __init__(self, timestamp, filter_name, triggered, input_values, threshold_values, data):
        self.timestamp = timestamp
        self.filter_name = filter_name
        self.triggered = triggered  # True if filter blocked trade
        self.input_values = input_values  # dict of all values checked
        self.threshold_values = threshold_values  # config value used
        self.data = data
    
    def to_dict_summarize(self):
        return {
            'filter_name': self.filter_name,
            'data': self.data
        }

class TradingDayFilter:
    """Determines if today is suitable for opening iron condor positions."""
    
    def __init__(self, config: TradeDayFilterConfig):
        self.config: TradeDayFilterConfig = config
        self.filter_configs = self._get_filter_configs()
        self.active_filters = self._get_active_filters(self.filter_configs)
        self.filter_history = {}
        self.failed_days = {}

    def can_trade_today(self, filter_data):
        params = FilteringParams(filter_data)
        current_date = params.current_date.date()
        can_trade_today = True
        if current_date not in self.filter_history:
            self.filter_history[current_date] = []
        
        todays_filter_results = {}
        for filter_obj in self.active_filters:
            should_skip_today_results = filter_obj.should_skip_trading(params)
            filter_data = filter_obj.to_dict(params)
            filter_result = FilterCheckResult(
                timestamp=params.current_date,
                filter_name=filter_data['name'],
                triggered=should_skip_today_results['triggered'],
                input_values=filter_data['input_values'],
                threshold_values=filter_data['threshold_values'],
                data=should_skip_today_results['data']
            )
            if todays_filter_results.get(filter_result.filter_name) is None:
                todays_filter_results[filter_result.filter_name] = filter_result
            self.filter_history[current_date].append(filter_result)

            if filter_result.triggered:
                if self.failed_days.get(current_date) is None:
                    self.failed_days[current_date] = {'filter_results': []}
                if self.failed_days[current_date].get(filter_result.filter_name) is None:
                    self.failed_days[current_date][filter_result.filter_name] = filter_result.to_dict_summarize()
            if can_trade_today and filter_result.triggered:
                last_failing_filter_result = filter_result
                can_trade_today = False

        
        day_result = {
            'date': current_date,
            'result': can_trade_today,
            'todays_filter_results': todays_filter_results
        }                  
        return day_result
    
    def get_filter_history(self):
        return self.filter_history

    def _is_earnings_week(self, underlying_symbol, today):
        """Filter out earnings announcement weeks"""
        pass
    
    def _is_vix_acceptable(self, current_vix):
        """Check if VIX is in acceptable range"""
        pass
    
    def _is_liquidity_sufficient(self, chain_analyzer):
        """Ensure option chain has tight spreads"""
        pass
    
    def _is_market_healthy(self):
        """Check correlation/market conditions"""
        pass
    
    def _get_reason_if_blocked(self):
        """Optional: return why trading is blocked today"""
        pass

    def _is_major_macro_event_day(self, current_date, macro_events):
        results = {'triggered': False, 'data': {}}
        data = {
            'current_date': current_date,
            'interpretation': 'MACRO_EVENT_DATE'
        }
        if current_date.date() in macro_events:
            results['triggered'] = True
        results['data'] = data
        return results

    def _is_overnight_gap_over_threshold(self, current_date, current_open, prev_close, current_atr, overnight_gap_atr_threshold):
        results = {'triggered': False, 'data': {}}
        if current_atr <= 0: 
            return results
        gap = abs(current_open - prev_close)
        gap_pct_atr = gap / current_atr
        data =  {
            'current_date': current_date,
            'current_open': current_open,
            'prev_close': prev_close,
            'current_atr': current_atr,
            'overnight_gap_atr_threshold': overnight_gap_atr_threshold,
            'gap': gap,
            'gap_pct_atr': gap_pct_atr,
            'rule_check': 'gap_pct_atr > overnight_gap_atr_threshold',
            'interpretation': ''
        }
        results['data'] = data
        results['triggered'] = gap_pct_atr > overnight_gap_atr_threshold
        return results

    def _is_vwap_over_threshold(self, current_price, current_vwap, current_atr, vwap_atr_multiplier):
        results = {'triggered': False, 'data': {}}
        vwap_threshold = vwap_atr_multiplier * current_atr
        vwap_delta =abs(current_price - current_vwap)
        data = {
            'current_price': current_price,
            'current_vwap': current_vwap,
            'current_atr': current_atr,
            'vwap_atr_multiplier': vwap_atr_multiplier,
            'vwap_threshold': vwap_threshold,
            'vwap_delta': vwap_delta,
            'rule_check': 'vwap_delta > vwap_threshold',
            'interpretation': ''
        }
        results['data'] = data
        results['triggered'] = vwap_delta > vwap_threshold
        return results

    def _is_bb_over_threshold(self, current_price, current_lower, current_middle, current_upper, bb_normalized_distance_threshold):
        results = {'triggered': False, 'data': {}}
        band_width = current_upper - current_lower
        current_price_sub_mid = abs(current_price - current_middle)    
        data = {
            'current_price': current_price,
            'current_lower': current_lower,
            'current_middle': current_middle,
            'current_upper': current_upper,
            'bb_normalized_distance_threshold': bb_normalized_distance_threshold,
            'current_price_sub_mid': current_price_sub_mid,
            'band_width': band_width,
            'normalized_distance': None,
            'rule_check': 'normalized_distance > bb_normalized_distance_threshold',
            'interpretation': ''
        }
        if band_width > 0:
            normalized_distance = current_price_sub_mid / (band_width / 2)
            data['normalized_distance'] = normalized_distance
            results['triggered'] = normalized_distance > bb_normalized_distance_threshold
        results['data'] = data
        return results

    def _is_rsi_over_threshold(self, current_rsi, rsi_oversold_threshold, rsi_overbought_threshold):
        results = {'triggered': False, 'data': {}}
        oversold = current_rsi < rsi_oversold_threshold
        overbought = current_rsi > rsi_overbought_threshold
        data = {
            'current_rsi': current_rsi,
            'rsi_oversold_threshold': rsi_oversold_threshold,
            'rsi_overbought_threshold': rsi_overbought_threshold,
            'oversold': oversold,
            'overbought': overbought,
            'rule_check': 'oversold or overbought',
            'interpretation': ''
        }
        results['data'] = data
        results['triggered'] = oversold or overbought
        return results

    def _is_adx_over_threshold(self, current_adx, adx_trend_threshold):
        results = {'triggered': False, 'data': {}}
        data = {
            'current_adx': current_adx,
            'adx_trend_threshold': adx_trend_threshold,
            'rule_check': 'current_adx > adx_trend_threshold',
            'interpretation': ''
        }
        results['data'] = data
        results['triggered'] = current_adx > adx_trend_threshold
        return results

    def _is_vix_over_threshold(self, vix, vix_threshold):
        results = {'triggered': False, 'data': {}}
        data = {
            'vix': vix,
            'vix_threshold': vix_threshold,
            'rule_check': 'vix > vix_threshold',
            'interpretation': ''
        }
        results['data'] = data
        results['triggered'] = vix > vix_threshold
        return results

    def _is_vix1d_over_threshold(self, vix_1d, vix_1d_threshold):
        results = {'triggered': False, 'data': {}}
        data = {
            'vix_1d': vix_1d,
            'vix_1d_threshold': vix_1d_threshold,
            'rule_check': 'vix_1d > vix_1d_threshold',
            'interpretation': ''
        }
        results['data'] = data
        results['triggered'] = vix_1d > vix_1d_threshold
        return results

    def _get_active_filters(self, filter_configs):
        # Then create your filters
        active_filters = []
        for filter_config in filter_configs:
            if getattr(self.config, filter_config['config_key']):
                filter_obj = DayTradeFilter(
                    name=filter_config['name'],
                    check_method=getattr(self, filter_config['method']),
                    params_builder=filter_config['params_builder'],
                    threshold_values=filter_config['threshold_values']
                )
                active_filters.append(filter_obj)
        return active_filters

    def _get_filter_configs(self):
        filter_configs = [
            {
                'name': 'VIXThreshold',
                'config_key': 'is_check_vix_threshold',
                'method': '_is_vix_over_threshold',
                'params_builder': lambda current_vix, **kwargs: [current_vix],
                'threshold_values': {
                    'vix_threshold': self.config.vix_threshold
                }
            },
            {
                'name': 'VIX1DThreshold',
                'config_key': 'is_check_vix1d_threshold',
                'method': '_is_vix1d_over_threshold',
                'params_builder': lambda current_vix1d, **kwargs: [current_vix1d],
                'threshold_values': {
                    'vix1d_threshold': self.config.vix1d_threshold
                }
            },
            {
                'name': 'MacroEvent',
                'config_key': 'is_check_macro_event',
                'method': '_is_major_macro_event_day',
                'params_builder': lambda current_date, **kwargs: [current_date],
                'threshold_values': {
                    'macro_events': self.config.MACRO_EVENTS
                }
            },
            {
                'name': 'OvernightGap',
                'config_key': 'is_check_overnight_gap',
                'method': '_is_overnight_gap_over_threshold',
                'params_builder': lambda current_date, current_open, prev_day_close, current_atr, **kwargs: 
                    [current_date, current_open, prev_day_close, current_atr],
                'threshold_values': {
                    'overnight_gap_atr_threshold': self.config.overnight_gap_atr_threshold
                }
            },
            {
                'name': 'VWAPThreshold',
                'config_key': 'is_check_vwap_threshold',
                'method': '_is_vwap_over_threshold',
                'params_builder': lambda current_price, current_vwap, current_atr, **kwargs: 
                    [current_price, current_vwap, current_atr],
                'threshold_values': {
                    'vwap_atr_multiplier': self.config.vwap_atr_multiplier
                }
            },
            {
                'name': 'BBThreshold',
                'config_key': 'is_check_bb_threshold',
                'method': '_is_bb_over_threshold',
                'params_builder': lambda current_date, current_price, current_bb, **kwargs: 
                    [current_date, current_price, current_bb['lower'], current_bb['middle'], current_bb['upper']],
                'threshold_values': {
                    'bb_normalized_distance_threshold': self.config.bb_normalized_distance_threshold
                }
            },
            {
                'name': 'RSIThreshold',
                'config_key': 'is_check_rsi_threshold',
                'method': '_is_rsi_over_threshold',
                'params_builder': lambda current_rsi, **kwargs: [current_rsi],
                'threshold_values': {
                    'rsi_oversold_threshold': self.config.rsi_oversold_threshold,
                    'rsi_overbought_threshold': self.config.rsi_overbought_threshold
                }
            },
            {
                'name': 'ADXThreshold',
                'config_key': 'is_check_adx_threshold',
                'method': '_is_adx_over_threshold',
                'params_builder': lambda current_adx, **kwargs: [current_adx],
                'threshold_values': {
                    'adx_trend_threshold': self.config.adx_trend_threshold
                }
            },
        ]
        return filter_configs

# mean_reversion_ok = (
#     self.rsi.IsReady and
#     self.bb.IsReady and
#     self.vwap.IsReady and
#     40 < self.rsi.Current.Value < 60 and
#     self.bb.LowerBand.Current.Value < price < self.bb.UpperBand.Current.Value and
#     abs(price - self.vwap.Current.Value) < vwap_threshold
# )


# # High-impact macro no-trade days
# MACRO_NO_TRADE_DAYS = {
#     # FOMC rate decisions
#     date(2025, 1, 29),
#     date(2025, 3, 19),
#     date(2025, 5, 7),

#     # CPI releases
#     date(2025, 2, 13),
#     date(2025, 3, 12),

#     # Non-Farm Payroll
#     date(2025, 2, 7),
#     date(2025, 3, 7),

#     # PCE inflation
#     date(2025, 2, 28),
# }


"""
Overnight gap

ADX

VWAP distance

Bollinger normalized distance

RSI

VIX / VIX1D

Macro event (context, not gate)

------------------------------------
For IC survival:

Gap

ADX

VWAP

Everything else is optimization.
----------------------------------
"""

"""
NO-TRADE DAY CHECKLIST (Iron Condor Strategy)

Skip trading on scheduled market event days such as FOMC rate decisions,
CPI, PCE, or NFP release mornings, major Federal Reserve speaker days,
or large index-weighted earnings days.

Skip days with strong trend or momentum behavior, including large
overnight gaps, early directional breakouts that hold without mean
reversion, strong sustained VWAP slope up or down, or elevated ADX
early in the session.

Skip days where implied volatility is extremely high, such as IV rank
above 80–85, panic-driven markets, volatility expansion days, or when
intraday ranges are already large early in the session.

Skip days where implied volatility is too low to justify selling
premium, such as IV rank below 20–25 or when premium does not adequately
compensate for tail risk.

Skip days with a large premarket move where price has already
approached or exceeded the expected move or when a clear directional
bias is established before the open.

Skip days when price is sitting near a magnet, including max pain,
large open-interest strikes, or prior day high or low levels, which
often precede late-session breakouts.

Avoid opening new iron condors late in the trading session due to
increased gamma risk and reduced liquidity creating asymmetric losses.
"""

"""
QuantConnect has support for
    getting earnings dates


QC does not have
    FOMC dates 
        can hardcode, there are 8 scheduled meetings per year
    CPI, PCE, NFP, Fed Speakers
        would need hardcode or pull from external economic calendar API
        API sources - Alpha Vantage, FRED, Investing.com
    
"""

    
