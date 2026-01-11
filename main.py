import json
from AlgorithmImports import *
from strategy.short_iron_condor_strategy import ShortIronCondorStrategy
from utils.logger import Logger
from models import PositionOrderStatus
from strategy.config import ShortIronCondorConfig, AlgorithmConfig, TradeDayFilterConfig, IronCondorScoringConfig
from portfolio.portfolio_manager import PortfolioManager
from selection.option_chain_analyzer import OptionChainAnalyzer
from execution.trade_manager import TradeManager
from strategy.trading_day_filter import TradingDayFilter
from selection.contract_selector import ContractSelector
from selection.iron_condor_finder import IronCondorFinder
from selection.iron_condor_scorer import IronCondorScorer
from analytics.trade_analytics import TradeAnalytics
from analytics.trade_snapshots import TradeSnapshots



class SimpleShortIronCondorStrategy(QCAlgorithm):
    def initialize(self):
        self.SetTimeZone(TimeZones.NewYork)
        self.ic_config = ShortIronCondorConfig()
        self.algo_config = AlgorithmConfig()

        

        self.set_start_date(self.algo_config.start_date)
        self.set_end_date(self.algo_config.end_date)
        self.set_cash(self.algo_config.initial_cash)
            
        self.trade_days_filters = {}
        self.vix1d = self.add_index('VIX1D', Resolution.DAILY).symbol
        self.vix = self.add_index('VIX', Resolution.DAILY).symbol
        
  
        self.add_equity(self.algo_config.symbol)
        option = self.add_option(self.algo_config.symbol, resolution=self.algo_config.resolution)
        option.set_data_normalization_mode(DataNormalizationMode.RAW)
        option.set_filter(self.init_filter)

        self._rsi = self.rsi(self.ic_config.symbol, 14, MovingAverageType.WILDERS, Resolution.MINUTE)

        self._adx = self.adx(self.ic_config.symbol, 14, Resolution.MINUTE)

        self._bb = self.bb(self.ic_config.symbol, 20, 2, MovingAverageType.SIMPLE, Resolution.MINUTE)
        self._vwap = self.vwap(self.ic_config.symbol)
        
        self._atr = self.atr(self.ic_config.symbol, 14, MovingAverageType.SIMPLE, Resolution.DAILY)
        
        self.prev_close_id = self.identity(self.ic_config.symbol, Resolution.DAILY, Field.CLOSE)

        self.prev_close = None

        self.logger = Logger(None, None)

        self.trading_day_filter_config = TradeDayFilterConfig()
        self.trading_day_filter = TradingDayFilter(self.trading_day_filter_config)
        self.trade_snapshots = TradeSnapshots()
        self.trade_analytics = TradeAnalytics(logger=self.logger, trade_snapshots=self.trade_snapshots)
        
        
        self.option_chain_analyzer = OptionChainAnalyzer(self, config=self.ic_config, logger=self.logger)
        self.trade_manager = TradeManager(algo=self, config=self.ic_config, logger=self.logger, option_chain_analyzer=self.option_chain_analyzer, trade_snapshots=self.trade_snapshots)
        self.iron_condor_scorer_config = IronCondorScoringConfig
        self.iron_condor_scorer = IronCondorScorer(config=self.iron_condor_scorer_config)
        self.contract_selector = ContractSelector(logger=self.logger)
        self.iron_condor_finder = IronCondorFinder(self.ic_config, self.logger, 
            self.contract_selector, 
            self.iron_condor_scorer,
            self.option_chain_analyzer)
        self.portfolio_manager = PortfolioManager(algo=self, config=self.ic_config, logger=self.logger)
        self.trade_manager.on_position_closed = self.portfolio_manager.on_position_closed
        self.trade_manager.on_position_opened = self.portfolio_manager.on_position_opened
        self.trade_manager.on_order_cancelled = self.portfolio_manager.on_order_cancelled
        self.trade_manager.on_order_submitted = self.portfolio_manager.on_order_submitted
        
        self.daily_bar_consolidator = TradeBarConsolidator(timedelta(days=1), start_time=timedelta(hours=9, minutes=30))
        self.daily_bar_consolidator.data_consolidated += self._on_daily_bar
        self.subscription_manager.add_consolidator(self.ic_config.symbol, self.daily_bar_consolidator)

        self.set_warm_up(20, Resolution.DAILY)

        self.short_iron_condor_strategy = ShortIronCondorStrategy(
            algo=self, 
            config=self.ic_config, 
            logger=self.logger, 
            portfolio_manager=self.portfolio_manager, 
            trade_manager=self.trade_manager, 
            iron_condor_finder=self.iron_condor_finder)

        self.schedule.on(self.date_rules.every_day(), self.time_rules.every(TimeSpan.from_minutes(self.algo_config.scheduling_minutes)), self.on_data_on_schedule)
        self.schedule.on(
            self.date_rules.every_day(),
            self.time_rules.before_market_close(self.ic_config.symbol, self.ic_config.liquidate_minutes_before_close, False),
            self.on_schedule_close_positions
        )

    def init_filter(self, data: OptionFilterUniverse):
        return self.short_iron_condor_strategy.init_filter(data)
    
        #     if not self.market_signal_is_good(...):
        # return
    
    def on_schedule_close_positions(self):
        now_time = self.time
        self.short_iron_condor_strategy.on_schedule_close_all()

    def on_data_on_schedule(self):
        if self.is_warming_up:
            return 
        technicals = self.get_technicals(self.ic_config.symbol, self.current_slice)
        if technicals:

            can_trade = self.can_trade_today(self.current_slice, technicals, self.trading_day_filter_config.is_trade_day_filter_active)
            
            self.short_iron_condor_strategy.on_schedule_iron_condor_strategy(can_trade, self.time, technicals)

        # main.py should be orchestration: “Should I run? What symbols? What dates?”    
        # A Strategy should own how it expresses the trade idea, which includes how it selects contracts.
        # Your PortfolioManager / TradeManager should stay strategy-agnostic (risk checks, sizing, order routing, lifecycle).


    # # Portfolio level - only reached if strategy says yes
    # if not self.portfolio_manager.can_open_position(...):
    #     return  # Risk/capacity issue


  
    def on_order_event(self, order_event: OrderEvent) -> None:
        self.short_iron_condor_strategy.on_order_event(order_event)
 
    # def on_data_scheduled(self):
    #     available_buying_power = self.portfolio.get_buying_power(self.config.algo_config, OrderDirection.BUY)
    #     value = self.portfolio.total_portfolio_value
    #     total_margin_used = self.portfolio.total_margin_used
    #     margin_remaining = self.portfolio.margin_remaining
    #     total_net_profit = self.portfolio.total_net_profit
    #     total_unrealised_profit = self.portfolio.total_unrealised_profit
    #     total_fees = self.portfolio.total_fees
    #     cash = self.portfolio.cash

    def _on_daily_bar(self, sender: object, consolidated_bar: TradeBar) -> None:
        self.prev_close = consolidated_bar.close
        pass
    
    def _get_trade_analytics(self):
        closed_positions = self.portfolio_manager.closed_positions
        results = self.trade_analytics.aggregate_trades(closed_positions)
        return results
        # left off on 12/28
        # make sure aggregte trades is correct, then put in object store
        # use research to make inferences about data
        # open trading up to more than once a day and at other times. 
        # just cast a wider net. then figure out which trades are the best to make
    
    def on_end_of_algorithm(self) -> None:
        filter_day_results = self.trading_day_filter.filter_history
        failed_filter_day_results = self.trading_day_filter.failed_days
        

        algo_config_json = self.get_algo_run_config_json()
        stats = self.short_iron_condor_strategy.on_end_of_algorithm()
        trade_analytics = self._get_trade_analytics()
        trade_snapshots = self.trade_snapshots.trade_snapshots

        algo_obj_unique_key = self.get_obj_store_unique_key()
        self.save_file_in_obj_store(algo_obj_unique_key, 'trade_analytics.json',trade_analytics)
        self.save_file_in_obj_store(algo_obj_unique_key, 'trade_snapshots.json',trade_snapshots)
        # self.save_file_in_obj_store('algo_config.json',algo_config_json)
        # self.save_file_in_obj_store('stats.json',stats)
        return None
    
    def get_technicals(self, symbol, data):

        # if not self.prev_close_id.is_ready:
        #     return
        current_date = self.time
        current_open =  self.securities[symbol].Open
        prev_close = self.prev_close
        current_time = self.time.strftime("%Y-%m-%d, %H:%M:%S")
        
        if not self.prev_close:
            return
        if not self._adx.is_ready:
            return
        current_adx = self._adx.current.value
        if not self._rsi.is_ready:
            return
        current_rsi = self._rsi.current.value

        if not self._atr.is_ready:
            return
        current_atr = self._atr.current.value

        if not self._bb.is_ready:
            return
        current_bb = {
            'middle': self._bb.middle_band.current.value,
            'upper': self._bb.upper_band.current.value,
            'lower': self._bb.lower_band.current.value
        }

        if not self._vwap.is_ready:
            return
        current_vwap = self._vwap.current.value

        price = self.securities[self.vix].price  # Always current

        current_vix = None
        if self.securities[self.vix]:
            current_vix = self.securities[self.vix].price
        
        current_vix1d = None
        if self.securities[self.vix1d]:
            current_vix1d = self.securities[self.vix1d].price
    
        current_price = self.securities[symbol].price
        trade_day_data = {
            'current_price': current_price,
            'current_date': current_time,
            'current_open': current_open,
            'prev_day_close': prev_close,
            'current_adx': current_adx,
            'current_rsi': current_rsi,
            'current_bb': current_bb,
            'current_vwap': current_vwap,
            'current_atr': current_atr,
            'current_vix': current_vix, 
            'current_vix1d': current_vix1d
        }
        return trade_day_data
    
    def can_trade_today(self, data, technicals, is_trade_day_filter_active: bool):
        if not is_trade_day_filter_active:
            return True
        trade_day_data = technicals
        if trade_day_data:
            can_trade_today_result = self.trading_day_filter.can_trade_today(trade_day_data)
            
            if not can_trade_today_result["result"]:
                if not can_trade_today_result['date'] in self.trade_days_filters:
                    self.trade_days_filters[can_trade_today_result['date']] = can_trade_today_result['todays_filter_results']

            return can_trade_today_result["result"]

    def get_algo_run_config_json(self):
        s_date = self.algo_config.start_date.strftime("%Y-%m-%d")
        e_date = self.algo_config.end_date.strftime("%Y-%m-%d")
        symbol = self.algo_config.symbol
        sch_min = self.algo_config.scheduling_minutes
        s_trd_h = self.ic_config.start_trading_minutes_since_open
        s_trd_m = self.ic_config.start_trading_minutes_since_open
        d_t_exp = self.ic_config.days_to_expiration
        sh_dlt_c = self.ic_config.short_call_delta_range[0]
        sh_dlt_p = self.ic_config.short_put_delta_range[0]
        pt_pct = self.ic_config.profit_target_percent
        mx_l_pct = self.ic_config.max_loss_percent
        # cls_a_h = self.ic_config.close_at_hour
        chk_me = self.trading_day_filter_config.is_check_macro_event
        chk_gap = self.trading_day_filter_config.is_check_overnight_gap
        chk_vwap = self.trading_day_filter_config.is_check_vwap_threshold
        chk_bb = self.trading_day_filter_config.is_check_bb_threshold
        chk_rsi = self.trading_day_filter_config.is_check_rsi_threshold
        chk_adx = self.trading_day_filter_config.is_check_adx_threshold

        return {
            "start_date": s_date,
            "end_date": e_date,
            "symbol": symbol,

            "scheduling_minutes": sch_min,

            "trading_window": {
                "start_hour": s_trd_h,
                "start_minute": s_trd_m,
                "days_to_expiration": d_t_exp
            },

            "delta_targets": {
                "short_call_delta": sh_dlt_c,
                "short_put_delta": sh_dlt_p
            },

            "risk_management": {
                "profit_target_percent": pt_pct,
                "max_loss_percent": mx_l_pct
            },

            "trading_day_filters": {
                "check_macro_event": chk_me,
                "check_overnight_gap": chk_gap,
                "check_vwap_threshold": chk_vwap,
                "check_bb_threshold": chk_bb,
                "check_rsi_threshold": chk_rsi,
                "check_adx_threshold": chk_adx
            }
        }

    def get_algo_run_config_msg(self):
        s_date = self.algo_config.start_date.strftime("%Y-%m-%d")
        e_date = self.algo_config.end_date.strftime("%Y-%m-%d")
        symbol = self.algo_config.symbol
        sch_min = self.algo_config.scheduling_minutes
        s_trd_h = self.ic_config.start_trading_minutes_since_open
        s_trd_m = self.ic_config.start_trading_minutes_since_open
        d_t_exp = self.ic_config.days_to_expiration
        sh_dlt_c = self.ic_config.short_call_delta_range[0]
        sh_dlt_p = self.ic_config.short_put_delta_range[0]
        pt_pct = self.ic_config.profit_target_percent
        mx_l_pct = self.ic_config.max_loss_percent
        # cls_a_h = self.ic_config.close_at_hour
        chk_me = self.trading_day_filter_config.is_check_macro_event
        chk_gap = self.trading_day_filter_config.is_check_overnight_gap
        chk_vwap = self.trading_day_filter_config.is_check_vwap_threshold
        chk_bb = self.trading_day_filter_config.is_check_bb_threshold
        chk_rsi = self.trading_day_filter_config.is_check_rsi_threshold
        chk_adx = self.trading_day_filter_config.is_check_adx_threshold

        

        run_config_msg = "\n".join([
            "==================== ALGO RUN CONFIG ====================",
            "",
            "Date Range",
            f"- Start Date: {s_date}",
            f"- End Date:   {e_date}",
            "",
            "Instrument",
            f"- Underlying Symbol: {symbol}",
            "",
            "Scheduling",
            f"- Evaluation Frequency (minutes): {sch_min}",
            "",
            "Trading Window",
            f"- Start Trading Time: {s_trd_h:02d}:{s_trd_m:02d}",
            "",
            "Iron Condor Structure",
            f"- Days to Expiration: {d_t_exp}",
            f"- Short Call Delta:   {sh_dlt_c}",
            f"- Short Put Delta:    {sh_dlt_p}",
            "",
            "Risk Management",
            f"- Profit Target (%): {pt_pct}",
            f"- Max Loss (%):      {mx_l_pct}",
            "",
            "Filters",
            f"- Macro Event Check Enabled: {chk_me}",
            f"- Overnight Gap Check:     {chk_gap}",
            f"- VWAP Threshold Check:    {chk_vwap}",
            f"- Bollinger Band Check:    {chk_bb}",
            f"- RSI Threshold Check:     {chk_rsi}",
            f"- ADX Threshold Check:     {chk_adx}",
            "",
            "========================================================"
        ])

        return run_config_msg

    def get_filter_config_result_message(self, trade_day_filter_results):
        r = trade_day_filter_results
        message = f"""

        """
    def get_algo_stats_message(self, stats):
        ac = stats['all_closing_stats']
        message = "\n".join([
            "==================== STRATEGY RESULTS ====================",
            "",
            "Strategy",
            "- Name: Iron Condor",
            "",
            "Position Summary",
            f"- Total Positions Opened: {stats['all_pos_count']}",
            f"- Total Positions Closed: {stats['close_pos_count']}",
            "",
            "Exit Breakdown",
            f"- Closed at Profit Target:     {stats['profit_target_count']}",
            f"- Closed at Loss Target:       {stats['loss_target_count']}",
            f"- Closed at Time (Close Hour): {stats['close_hour_target_count']}",
            "",
            "Performance Metrics",
            f"- Total PnL ($):        {ac['total_pnl']:.2f}",
            f"- Total PnL * 100($):   {ac['total_pnl']*100:.2f}",
            f"- Average PnL (%):      {ac['avg_pnl_pct']:.2f}%",
            f"- Average Win (%):      {ac['avg_win_pct']:.2f}%",
            f"- Average Loss (%):     {ac['avg_lose_pct']:.2f}%",
            "",
            "Win / Loss Stats",
            f"- Winning Trades: {ac['num_wins']}",
            f"- Losing Trades:  {ac['num_losses']}",
            "",
            "==========================================================",
        ])

        return message

    def get_obj_store_unique_key(self):
        algorithm_id = self.algorithm_id
        run_time = self.time.strftime("%Y-%m-%d_%H-%M-%S") 
        return f"{algorithm_id}_{run_time}"

    def save_file_in_obj_store(self, unique_key, filename, message):
        obj_key = f"{unique_key}_{filename}"
        import json
        msgstr = json.dumps(message)
        self.object_store.save(obj_key, msgstr)

    def save_message_in_obj_store(self, message):
        algorithm_id = self.algorithm_id
        # Use a consistent, sortable date format (e.g., ISO 8601)
        run_time = self.time.strftime("%Y-%m-%d_%H-%M-%S") 
        # %Y-%m-%d, %H:%M:%S
        
        # Combine them to create a unique key
        unique_key = f"{algorithm_id}_{run_time}_data_key"
        self.object_store.save(unique_key, message)

    def notify_email(self, message):
        algorithm_id = self.algorithm_id
        # Use a consistent, sortable date format (e.g., ISO 8601)
        run_time = self.time.strftime("%Y-%m-%d_%H-%M-%S") 
        
        # Combine them to create a unique key
        unique_key = f"{algorithm_id}_{run_time}_data_key.txt"

        self.notify.email("lucerodavid1010@gmail.com", "QC algo results", "QC algo results", message[:9000])
