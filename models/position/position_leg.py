# region imports
from AlgorithmImports import *
# endregion

class PositionLeg:
    def __init__(self, contract: OptionContract, tag, sign_multiplier):
        self.contract = contract
        self.order_ticket: OrderTicket = None
        self.sign_multiplier: int = sign_multiplier
        self.tag = tag
        self.expiry = contract.expiry
        self.symbol_canonical = contract.symbol.canonical
        self.symbol = contract.symbol
        self.strike = contract.strike
        self.fill_price = None
    
    def dte(self, now):
        return (self.contract.expiry.date() - now.date()).days

    def get_contract_prices(self):
        bid = self.contract.bid_price * self.sign_multiplier
        ask = self.contract.ask_price * self.sign_multiplier
        mid = ((self.contract.bid_price + self.contract.ask_price) / 2) * self.sign_multiplier
        return {
            'bid': bid, 'ask': ask, 'mid': mid
        }

    def get_order_fill_price(self):
        return self.fill_price
    
    def get_order_status(self):
        if self.order_ticket:
            return self.order_ticket.status
        else: return None
    
    def is_filled(self):
        return self.order_ticket and self.order_ticket.status == OrderStatus.FILLED
    
    def get_contract_type(self):
        return self.contract.right

    def equals_symbol(self, symbol):
        return self.symbol.equals(symbol)
    
    def set_order_ticket(self, order_ticket: OrderTicket):
        self.order_ticket = order_ticket
    
    def to_dict(self):
        return {
            'tag': self.tag,
            'sign_multiplier': self.sign_multiplier,
            'expiry': str(self.expiry),
            'symbol_canonical': str(self.symbol_canonical),
            'strike': self.strike,
            'fill_price': self.fill_price,
            'is_filled': self.is_filled()
        }
