# region imports
from AlgorithmImports import *
from portfolio.portfolio_manager import PortfolioManager
from execution.trade_manager import TradeManager
from utils.logger import Logger
from models import IronCondorPosition, PositionStatus, FinderResult, PositionOrderStatus
from selection.contract_selector import ContractSelector
from strategy.config import ContractSelectionConfig
from selection.iron_condor_finder import IronCondorFinder
# endregion

class ShortIronCondorStrategy:
    def __init__(self, algo, config, logger: Logger, portfolio_manager: PortfolioManager, 
        trade_manager: TradeManager, iron_condor_finder: IronCondorFinder):
        self.algo = algo
        self.config = config
        self.logger = logger
        self.portfolio_manager = portfolio_manager
        self.iron_condor_finder = iron_condor_finder
        self.trade_manager = trade_manager
        self.start_trading_at_time = None
        self.symbol = self.config.symbol
        self.dte_target = self.config.days_to_expiration
        self.last_date = None
        

    def init_filter(self, data: OptionFilterUniverse):
        return data.include_weeklys().expiration(0, 0).strikes(-50,50)

    def on_data(self, data):
        pass

    def on_schedule_iron_condor_strategy(self, can_trade, current_time, technicals):  
        # Thin orchestration - delegate everything
        underlying_price = self.algo.securities[self.symbol].price
        current_time = self.algo.time
        self.reset_last_date()
        
        can_trade_pm = self.can_trade()
        current_positions = self.portfolio_manager.get_current_positions()
        if len(current_positions.keys()) > 0:
            self.logger.info(f'found {len(current_positions.keys())} current positions')
            for k, current_position in list(current_positions.items()):
                self.trade_manager.manage_position(current_position, k)
        
        if can_trade and can_trade_pm and self.can_open_position():
            self.logger.info(f'no current positions and can open position {self.algo.time}')
            position = self._get_iron_condor_position(self.symbol, current_time, underlying_price)
            if position:
                position.technicals = technicals
                self.logger.info(f'found position to open on {self._get_current_date_str(current_time)}')
                self.trade_manager.open_position(position)  
            # else:
                # self.logger.info(f'did not find position to open on {self._get_current_date_str(current_time)}')

    def _get_current_date_str(self, now_time):
        return now_time.date().strftime("%Y-%m-%d")
  
    def _get_iron_condor_position(self, symbol, now_time, underlying_price):
        sel_cfg = self._get_contract_selector_config()
        chain = self.get_chain(symbol)
        finder_result: FinderResult = self.iron_condor_finder.find_best(now_time, symbol, underlying_price, chain, sel_cfg)
        if not finder_result.had_error:
            best_ic = finder_result.get_best_ic_overall()
            if best_ic:
                long_put = best_ic.put.long
                short_put = best_ic.put.short
                long_call = best_ic.call.long
                short_call = best_ic.call.short
                position = IronCondorPosition(self.symbol, long_put, short_put, short_call, long_call)
                position.ic_candidate = best_ic
                return position
        return None

    def _get_contract_selector_config(self) -> ContractSelectionConfig:
        sel_cfg = ContractSelectionConfig(
            dte_range=self.config.dte_range,
            short_call_delta_range=self.config.short_call_delta_range,
            short_put_delta_range=self.config.short_put_delta_range,
            spread_width_range=self.config.spread_width_range,
            is_use_fixed_delta=self.config.is_use_fixed_delta,
            short_delta_fixed_target=self.config.short_delta_fixed_target,
            is_use_fixed_spread_width=self.config.is_use_fixed_spread_width,
            fixed_spread_width=self.config.fixed_spread_width
        )
        return sel_cfg
  
    def on_order_event(self, order_event: OrderEvent):
        return self.trade_manager.on_order_event(order_event)

    
    def on_end_of_algorithm(self):
        return self.portfolio_manager.calculate_stats()


    def on_schedule_close_all(self): 
        open_pos = self.portfolio_manager.open_positions.copy()
        for k, p in open_pos.items():  
            if p.status not in (PositionStatus.CLOSE_SUBMITTED, PositionStatus.CLOSED):
                p.exit_reason = "FAILSAFE_BEFORE_CLOSE"
                self.trade_manager.handle_close_position(p, k)
                

    def get_chain(self, symbol):
        if self.algo.current_slice.option_chains.count == 0 or not self.algo.current_slice.option_chains[symbol]:
            return None
        else:
            return self.algo.current_slice.option_chains[symbol]
        
    def get_minutes_since_open(self):
        now_minutes_since_open = (
            self.algo.time.hour * 60 + self.algo.time.minute
        ) - (9 * 60 + 30)
        return now_minutes_since_open

    def is_within_trading_window(self):
        return (
            self.config.start_minutes_since_open
            <= self.now_minutes_since_open
            <= self.config.end_minutes_since_open
        )

    def get_trading_window_time(self):
        start_trading_time = datetime(self.algo.time.year, self.algo.time.month, self.algo.time.day, 
                            self.config.start_trading_hour, self.config.start_trading_minute)
        end_trading_time = datetime(self.algo.time.year, self.algo.time.month, self.algo.time.day, 
                            self.config.end_trading_hour, self.config.end_trading_minute)
        return start_trading_time, end_trading_time
        
    def is_time_in_trading_window_hist(self):
        start_trading_time, end_trading_time = self.get_trading_window_time()
        
        c_time = self.algo.time.strftime("%Y-%m-%d, %H:%M:%S")

        if end_trading_time >= self.algo.time >= start_trading_time:
            return True
        return False

    def minutes_since_open(self, symbol):
        ex = self.algo.securities[symbol].exchange
        last_open = ex.hours.get_previous_market_open(self.algo.time, False)
        return (self.algo.time - last_open).total_seconds() / 60

    def minutes_to_close(self, symbol):
        ex = self.algo.securities[symbol].exchange
        next_close = ex.hours.get_next_market_close(self.algo.time, False)
        return (next_close - self.algo.time).total_seconds() / 60

    def is_time_in_trading_window(self, symbol):
        if not self.is_window_possible_today(symbol):
            self.Log("No-trade: session too short for configured window")
            return False
        ms_open = self.minutes_since_open(symbol)
        mt_close = self.minutes_to_close(symbol)

        # Two-sided window rule
        if ms_open < self.config.start_trading_minutes_since_open:
            return False

        if mt_close < self.config.end_trading_minutes_before_close:
            return False

        return True
    
    def is_window_possible_today(self, symbol):
        ex = self.algo.securities[symbol].exchange
        # GetNextMarketOpen(current_time
        open_dt = ex.hours.get_previous_market_open(self.algo.time, False)
        close_dt = ex.hours.get_next_market_close(open_dt, False) # close for that same session
        session_minutes = (close_dt - open_dt).total_seconds() / 60

        required = self.config.start_trading_minutes_since_open + self.config.end_trading_minutes_before_close
        return session_minutes > required

    def can_open_position(self):
        if self.is_time_in_trading_window(self.config.symbol): 
            if self.config.is_check_max_trades_per_day and self.config.max_trades_per_day > len(self.portfolio_manager.trades_today):
                if self.config.is_check_max_open_positions and self.config.max_open_positions > self.get_num_positions_open():
                    return True
        return False
    
    def reset_last_date(self):
        if self.last_date != self.algo.time.date():
            self.portfolio_manager.trades_today = []
            self.last_date = self.algo.time.date()

    def get_num_positions_open(self):
        return len(self.portfolio_manager.open_positions)

    def can_trade(self):
        can_trade = True
        if not self.algo.is_market_open(self.config.symbol):
            can_trade = False
        if self.algo.current_slice.option_chains.count == 0 or not self.algo.current_slice.option_chains[self.config.symbol]:
            can_trade = False
        
        return can_trade



# holdings = self.portfolio[self._symbol]
        # # Check the holding quantity of the security.
        # quantity = holdings.quantity
        # # Check the investing status of the security.
        # invested = holdings.invested
        # # Check if the strategy is long or short the security.
        # is_long = holdings.is_long
        # is_short = holdings.is_short
