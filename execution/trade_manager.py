# region imports
from AlgorithmImports import *
from utils.logger import Logger
from selection.option_chain_analyzer import OptionChainAnalyzer
from models.iron_condor_position import IronCondorPosition, IronCondorLegs, PositionStatus
from models.position_order_status import PositionOrderStatus
from models.trade_group import TradeGroup, TradeOrder
# endregion

# Execution layer
# Order execution
# Trade lifecycle manager (entry , management, exit)
# Order Management logic

class TradeManager:
    def __init__(self, algo, config, logger: Logger, option_chain_analyzer: OptionChainAnalyzer):
        self.algo = algo
        self.config = config
        self.logger = logger
        self.option_chain_analyzer = option_chain_analyzer
        self.trade_groups = {}
        self.order_to_group = {}
        self.on_position_opened = None
        self.on_position_closed = None
        self.on_order_cancelled = None
        self.on_order_submitted = None

    
    def buy(self, position: IronCondorPosition, num_orders: int, tag):
        underlying_price = self.algo.securities[self.config.symbol].price
        position.entry_time = self.algo.time
        position.underlying_at_buy = underlying_price
        order_tickets = self.algo.buy(position.get_qc_strategy("OPEN"), num_orders, tag=tag)
        return order_tickets

    def sell(self, position: IronCondorPosition, num_orders: int, tag):
        underlying_price = self.algo.securities[self.config.symbol].price
        position.exit_time = self.algo.time
        position.underlying_at_sell = underlying_price
        order_tickets = self.algo.sell(position.get_qc_strategy("CLOSE"), num_orders, tag=tag)
        return order_tickets

    def manage_position(self, position: IronCondorPosition, trade_group_id):
        position_status = position.get_position_status()
        position_status_handler = self.get_status_handler(position_status)
        position_status_handler(position, trade_group_id)

    def calculate_position_cost(self, order_tickets):
        """Calculate actual cost/proceeds from filled tickets"""
        total = 0.0
        for ticket in order_tickets:
            # quantity_filled is signed (negative for sells, positive for buys)
            # So this automatically gives you the right sign
            total += ticket.average_fill_price * ticket.quantity_filled
        
        # Multiply by 100 for actual dollar amount (option contract multiplier)
        return total * 100

    def get_last_price(self, symbol):
        return self.algo.get_last_price(symbol)

    def get_similar_position_from_chain(self, position: IronCondorPosition) -> IronCondorLegs:
        short_put, short_call, long_put, long_call = None, None, None, None
        
        short_put = self.option_chain_analyzer.get_contract_from_chain(position.get_opening_legs().get_short_put(), position.symbol)
        short_call = self.option_chain_analyzer.get_contract_from_chain(position.get_opening_legs().get_short_call(), position.symbol)
        long_put = self.option_chain_analyzer.get_contract_from_chain(position.get_opening_legs().get_long_put(), position.symbol)
        long_call = self.option_chain_analyzer.get_contract_from_chain(position.get_opening_legs().get_long_call(), position.symbol)

        if all(c != None for c in [short_put, short_call, long_put, long_call]):
            # self.opening_legs = IronCondorLegs(order_type, long_put, short_put, short_call, long_call)
            # def __init__(self, order_type, long_put_contract: OptionContract, short_put_contract: OptionContract, short_call_contract: OptionContract, long_call_contract: OptionContract):
    
            return IronCondorLegs("LONG", long_put, short_put, short_call, long_call)
        else: return None
        

    def get_pnl_estimate(self, position: IronCondorPosition, closing_legs: IronCondorLegs):
        try:
            closing_prices = closing_legs.get_buy_prices()
            to_open_actual_cost = position.get_opening_total_fill_price()
            opening_credit = abs(to_open_actual_cost * 100)

            # Three scenarios for closing:
            best_pnl = opening_credit - closing_prices["bid"]
            mid_pnl = opening_credit - closing_prices["mid"]
            worst_pnl = opening_credit - closing_prices["ask"]
            best_percent = (best_pnl / opening_credit) * 100
            mid_percent = (mid_pnl / opening_credit) * 100
            worst_percent = (worst_pnl / opening_credit) * 100
            
            return {
                'best': best_pnl,
                'mid': mid_pnl,
                'worst': worst_pnl,
                'best_percent': best_percent,
                'mid_percent': mid_percent,
                'worst_percent': worst_percent
            }
        except Exception as e:
            self.logger.error(f"Error calculating current close cost: {str(e)}")
            return None



    def get_status_handler(self, position_status: PositionStatus):
        handler = self.on_wait
        
        if position_status == PositionStatus.SUBMITTED:
            return self.on_wait
        if position_status == PositionStatus.OPENED:
            return self.manage_opened_position
        
        # INVALID = immediate error
        if position_status == PositionStatus.INVALID:
            handler = self.on_error_invalid_state
        
        # SUCCESS = both filled
        if position_status == PositionStatus.FILLED:
            handler = self.on_success
        
        # close or open partially filled - try wait for all to be filled
        if position_status == PositionStatus.PARTIALLY_FILLED:
            handler = self.on_wait
        
        # PARTIAL = investigate why
        if position_status == PositionStatus.PARTIAL:
            handler = self.on_investigate_partial
        
        # CANCELED = handle it (cancel counterpart, update hist)
        if position_status == PositionStatus.CANCELED:
            handler = self.on_handle_cancellation

        if position_status == PositionStatus.FILLED:
            handler = self.on_open_order_filled
        
        # Everything else (SUBMITTED, NONE) = wait
        # This includes: (SUBMITTED, NONE), (SUBMITTED, SUBMITTED), (FILLED, NONE), (FILLED, SUBMITTED), etc.
        return handler

    def on_error_invalid_state(self, position: IronCondorPosition):
        position.cancel_all_tickets()
        return
    def on_investigate_partial(self, position: IronCondorPosition, trade_group_id):
        self.on_wait(position, trade_group_id)
        return
    def on_handle_cancellation(self, position: IronCondorPosition):
        position.cancel_all_tickets()
        return
    def on_wait(self, position: IronCondorPosition, trade_group_id):
        return
    def on_open_order_filled(self, position: IronCondorPosition):
        return

    def on_success(self, position: IronCondorPosition):
        return 
    
    def handle_close_position(self, position, trade_group_id = None, closing_legs = None, get_pnl_estimate = None):
        if not closing_legs:
            closing_legs: IronCondorLegs = self.get_similar_position_from_chain(position)
        
        self.close_position(position, closing_legs, trade_group_id)



    def manage_opened_position(self, position: IronCondorPosition, trade_group_id):
        underlying_price = self.algo.securities[self.config.symbol].price
        self.logger.info(f'managing position on {self.algo.time}')
        self.logger.info(f'underlying at manage: {underlying_price}')

        closing_legs: IronCondorLegs = self.get_similar_position_from_chain(position)
        pnl = self.get_pnl_estimate(position, closing_legs)

        self.logger.info(f'estimated pnl for position: {pnl["mid_percent"]}')

        if pnl["mid_percent"] >= self.config.profit_target_percent:
            position.exit_reason = "PROFIT_TARGET"
            return self.handle_close_position(position, trade_group_id, closing_legs, pnl)
        
        if pnl["mid_percent"] <= self.config.max_loss_percent:
            position.exit_reason = "LOSS_TARGET"
            return self.handle_close_position(position, trade_group_id, closing_legs, pnl)
        
        if self.is_minutes_before_close():
            position.exit_reason = "CLOSE_BEFORE_CLOSE_TARGET"
            return self.handle_close_position(position, trade_group_id, closing_legs, pnl)

    # exchange = self.Securities[self.underlying].Exchange
    # minutes_to_close = (exchange.Hours.GetNextMarketClose(self.Time, False) - self.Time).total_seconds() / 60

    # if minutes_to_close < 60:  # pick your window
    #     return

    def is_minutes_before_close(self):
        exchange = self.algo.securities[self.config.symbol].exchange
        minutes_to_close = (exchange.hours.get_next_market_close(self.algo.time, False) - self.algo.time).total_seconds() / 60

        if minutes_to_close <= self.config.close_minutes_before_close:
            return True
        return False
        
    def close_position(self, position, closing_legs, trade_group_id):
        underlying_price = self.algo.securities[self.config.symbol].price
        position.set_closing_legs(closing_legs)
        
        self.logger.info(f'closing position on {self.algo.time}')
        self.logger.info(f'underlying at close: {underlying_price}')
        self.logger.info(f'closing legs: ' + position.get_closing_legs_strikes_json())
        
        
        trade_group = self.trade_groups[trade_group_id]
        #self.on_order_submitted(position, trade_group)
        tag = f"{trade_group_id}:CLOSE"
        orders: list[OrderTicket] = self.sell(position, 1, tag)
        position.status = PositionStatus.CLOSE_SUBMITTED
        return trade_group_id

    # def find_position(self, symbol):
    #     return self.option_chain_analyzer.find_position(symbol)

    def open_position(self, position: IronCondorPosition):
        underlying_price = self.algo.securities[self.config.symbol].price
        c_time = self.algo.time.strftime("%Y-%m-%d, %H:%M:%S")
        self.logger.info(f'opening position on {self.algo.time}')
        self.logger.info(f'underlying at open: {underlying_price}')
        self.logger.info(f'opening legs: ' + position.get_opening_legs_strikes_json())
        
        import uuid
        trade_group_id = str(uuid.uuid4())
        trade_group = TradeGroup(trade_group_id, position.total_legs, position.symbol, position.name)
        self.trade_groups[trade_group_id] = trade_group
        
        position.status = PositionStatus.SUBMITTED
        self.on_order_submitted(position, trade_group)

        tag = f"{trade_group_id}:OPEN"
        orders: list[OrderTicket] = self.buy(position, 1, tag)
        return trade_group_id

    def _cancel_trade_group_orders(self, trade_group_id, order_group_type):
        """Cancel all remaining orders in a trade group"""
        trade_group = self.trade_groups[trade_group_id]
        if order_group_type == 'OPEN':
            for o in trade_group.opening_orders:
                if not trade_group.is_order_of_status("OPEN", o.order_id, "FILLED"):
                    self.algo.transactions.cancel_order(o.order_id)
            # del self.trade_groups[trade_group_id]
        elif order_group_type == 'CLOSE':
            for o in trade_group.closing_orders:
                if not trade_group.is_order_of_status("CLOSE", o.order_id, "FILLED"):
                    self.algo.transactions.cancel_order(o.order_id)


    def _on_filled_order(self, order_event: OrderEvent, trade_group_id, order_type):
        order_id = order_event.order_id
        trade_group = self.trade_groups[trade_group_id]
        # Track this filled order
        if order_type == "OPEN":
            trade_order = trade_group.get_opening_order(order_id)
            trade_order.fill_price = order_event.fill_price
            trade_group.set_order_status(order_id, order_type, "FILLED")
            if trade_group.are_all_opening_filled():
                if self.on_position_opened:
                    self.on_position_opened(trade_group)
        elif order_type == "CLOSE":
            trade_order = trade_group.get_closing_order(order_id)
            trade_group.set_order_status(order_id, order_type, "FILLED")
            trade_order.fill_price = order_event.fill_price
            if trade_group.are_all_orders_of_status("CLOSE", "FILLED"):
                # Only NOW fire the callback - entire position is open
                if self.on_position_closed:
                    self.on_position_closed(trade_group)
                    # Optional: clean up completed trade
                    # del self.trade_groups[trade_group_id]

            


    def _on_cancelled_order(self, order_event: OrderEvent, trade_group_id, order_type):
        order_id = order_event.order_id
        trade_group_id = self.order_to_group[order_id]
        trade_group = self.trade_groups[trade_group_id]
        
        self._cancel_trade_group_orders(trade_group_id, order_type)
        self.on_order_cancelled(trade_group, order_group_type = order_type)

    def on_order_event(self, order_event: OrderEvent):
        """Handle order fills/cancellations"""
        order_id = order_event.order_id
        order_status = order_event.ticket.status
        tag = order_event.ticket.tag
        
        if tag == None:
            return
            # getting none tag here for some reason
            # seems to be only when is_check_adx_threshold is true
        # Parse the tag
        if ":" not in tag:
            return  # Skip if not our tagged order
        
        trade_group_id, order_type = tag.split(":", 1)

        if trade_group_id not in self.trade_groups.keys():
            return # order not in trade groups so skip
        
        trade_group = self.trade_groups[trade_group_id]

        if not order_id in self.order_to_group.keys():
            self.order_to_group[order_id] = trade_group_id

        if order_status == OrderStatus.SUBMITTED:
            if order_type == "OPEN":
                if not trade_group.is_order_in_opening(order_id):
                    trade_group.add_opening_order(order_id)
                trade_group.set_order_status(order_id, order_type, "SUBMITTED")
                trade_group.get_opening_order(order_id).symbol = order_event.symbol
            if order_type == "CLOSE":
                if not trade_group.is_order_in_closing(order_id):
                    trade_group.add_closing_order(order_id)
                trade_group.set_order_status(order_id, order_type, "SUBMITTED")   
                trade_group.get_closing_order(order_id).symbol = order_event.symbol  
                
        if order_status == OrderStatus.FILLED:
            self._on_filled_order(order_event, trade_group_id, order_type)
        
        elif order_status == OrderStatus.CANCELED:
            self._on_cancelled_order(order_event, trade_group_id, order_type)
