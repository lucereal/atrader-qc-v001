# region imports
from AlgorithmImports import *
from position_order_status import PositionOrderStatus
from portfolio_manager import PortfolioManager
from trade_manager import TradeManager
from logger import Logger
from iron_condor_position import IronCondorPosition
from contract_selector import ContractSelector
from config import ContractSelectionConfig
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

    def init_filter(self, data: OptionFilterUniverse):
        return data.include_weeklys().expiration(0, 0).strikes(-50,50)

    def on_data(self, data):
        pass

    def on_schedule_iron_condor_strategy(self, can_trade, current_time):  
        # Thin orchestration - delegate everything
        underlying_price = self.algo.securities[self.symbol].price
        current_time = self.algo.time

        self.portfolio_manager.check_portfolio()
        can_trade_pm = self.portfolio_manager.can_trade()
        current_positions = self.portfolio_manager.get_current_positions()
        if len(current_positions.keys()) > 0:
            self.logger.info(f'found {len(current_positions.keys())} current positions')
            for k, current_position in list(current_positions.items()):
                self.trade_manager.manage_position(current_position, k)
        elif can_trade and can_trade_pm and self.portfolio_manager.can_open_position():
            self.logger.info(f'no current positions and can open position {self.algo.time}')
            position = self._get_iron_condor_position(self.symbol, current_time, underlying_price)
            if position:
                self.trade_manager.open_position(position)  
            else:
                self.logger.info(f'didnt find position to open')

  
    def _get_iron_condor_position(self, symbol, now_time, underlying_price):
        sel_cfg = self._get_contract_selector_config()
        chain = self.get_chain(symbol)
        # def find_best(self, now_time, symbol, underlying_price, chain, sel_config: ContractSelectionConfig):
        iron_condor_candidates = self.iron_condor_finder.find_best(now_time, symbol, underlying_price, chain, sel_cfg)
        best_candidate = iron_condor_candidates['best']
        if best_candidate and best_candidate['ic']:
            best_ic = best_candidate['ic']
            self._check_candidate_data(best_ic)
            long_put = best_ic.put.long
            short_put = best_ic.put.short
            long_call = best_ic.call.long
            short_call = best_ic.call.short
            position = IronCondorPosition(self.symbol, long_put, short_put, short_call, long_call)
            return position
        else: 
            return None
    def _check_candidate_data(self, ic_candidate):
        if ic_candidate and ic_candidate["data"]:
            data = ic_candidate["data"]
            return data
        return None

    def _get_contract_selector_config(self) -> ContractSelectionConfig:
        sel_cfg = ContractSelectionConfig(
            dte_range=self.config.dte_range,
            short_call_delta_range=self.config.short_call_delta_range,
            short_put_delta_range=self.config.short_put_delta_range,
            spread_width_range=self.config.spread_width_range,
        )
        return sel_cfg
  
    def on_order_event(self, order_event: OrderEvent):
        return self.trade_manager.on_order_event(order_event)

    
    def on_end_of_algorithm(self):
        return self.portfolio_manager.calculate_stats()


    def get_chain(self, symbol):
        if self.algo.current_slice.option_chains.count == 0 or not self.algo.current_slice.option_chains[symbol]:
            return None
        else:
            return self.algo.current_slice.option_chains[symbol]
        

# holdings = self.portfolio[self._symbol]
        # # Check the holding quantity of the security.
        # quantity = holdings.quantity
        # # Check the investing status of the security.
        # invested = holdings.invested
        # # Check if the strategy is long or short the security.
        # is_long = holdings.is_long
        # is_short = holdings.is_short
