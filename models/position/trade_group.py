# region imports
from AlgorithmImports import *
# endregion


class TradeOrder:
    def __init__(self, order_id):
        self.order_id = order_id
        self.fill_price = None
        self.status = None
        # SUBMITTED, FILLED, CANCELED, INVALID?

class TradeGroup:
    def __init__(self, trade_group_id, total_legs, symbol, strategy):
        self.trade_group_id = trade_group_id
        self.opening_orders: list[TradeOrder] = []
        self.closing_orders: list[TradeOrder] = []
        self.total_legs = total_legs
        self.symbol = symbol
        self.strategy = strategy
        
    def is_order_in_opening(self, order_id):
        return any(o.order_id == order_id for o in self.opening_orders)
    
    def is_order_in_closing(self, order_id):
        return any(o.order_id == order_id for o in self.closing_orders)

    def add_opening_order(self, order_id):
        if not self.is_order_in_opening(order_id):
            trade_order = TradeOrder(order_id)
            self.opening_orders.append(trade_order)
    
    def add_closing_order(self, order_id):
        if not self.is_order_in_closing(order_id) and not self.is_order_in_opening(order_id):
            trade_order = TradeOrder(order_id)
            self.closing_orders.append(trade_order)
    
    def get_opening_order(self, order_id) -> TradeOrder:
        return next((o for o in self.opening_orders if o.order_id == order_id), None)

    def get_closing_order(self, order_id) -> TradeOrder:
        return next((o for o in self.closing_orders if o.order_id == order_id), None)
    
    def are_all_orders_of_status(self, order_type, status):
        if order_type == "OPEN":
            if len(self.opening_orders) == self.total_legs:
                if all(o.status == status for o in self.opening_orders):
                    return True
        elif order_type == "CLOSE":
            if len(self.closing_orders) == self.total_legs:
                if all(o.status == status for o in self.closing_orders):
                    return True
        return False
        
    def are_all_opening_filled(self):
        if len(self.opening_orders) == self.total_legs:
            if all(o.status == "FILLED" for o in self.opening_orders):
                return True
        return False
    
    def are_all_closing_filled(self):
        if len(self.closing_orders) == self.total_legs:
            if all(o.status == "FILLED" for o in self.closing_orders):
                return True
        return False
    
    def get_opening_avg_fill_price(self):
        avg_fill_price = sum(o.fill_price for o in self.opening_orders) / self.total_legs
    
    def get_closing_avg_fill_price(self):
        avg_fill_price = sum(o.fill_price for o in self.closing_orders) / self.total_legs

    def is_order_of_status(self, order_type, order_id, status):
        if order_type == "OPEN":
            if self.get_opening_order(order_id).status == status:
                return True
        elif order_type == "CLOSE":
            if self.get_closing_order(order_id).status == status:
                return True
        return False
    
    def set_order_status(self, order_id, order_type, status):
        if order_type == "OPEN":
            if self.is_order_in_opening(order_id):
                self.get_opening_order(order_id).status = status
        elif order_type == "CLOSE":
            if self.is_order_in_closing(order_id):
                self.get_closing_order(order_id).status = status
