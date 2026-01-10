# region imports
from AlgorithmImports import *
from position_order_status import PositionOrderStatus
import json
# endregion

class PositionStatus(Enum):
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    SUBMITTED = "SUBMITTED"
    INVALID = "INVALID"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    PARTIAL = "PARTIAL"
    PARTIALLY_CANCELED_AND_PENDING = "PARTIALLY_CANCELED_AND_PENDING"
    INVALID_TICKET_COUNT = "INVALID_TICKET_COUNT"
    NONE = "NONE"
    OPENED = "OPENED"
    SUBMITTED = "SUBMITTED"
    CLOSED = "CLOSED"

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

class IronCondorLegs:
    LONG_PUT = "LONG_PUT"
    SHORT_PUT = "SHORT_PUT"
    SHORT_CALL = "SHORT_CALL"
    LONG_CALL = "LONG_CALL"
    
    def __init__(self, order_type, long_put_contract: OptionContract, short_put_contract: OptionContract, short_call_contract: OptionContract, long_call_contract: OptionContract):
        if long_put_contract.strike >= short_put_contract.strike:
            pass
        if long_call_contract.strike <= short_call_contract.strike:
            pass
        if short_put_contract.strike >= short_call_contract.strike:
            pass
        if order_type == "SHORT":
            self.legs = {
                self.LONG_PUT: PositionLeg(long_put_contract, self.LONG_PUT, 1),
                self.SHORT_PUT: PositionLeg(short_put_contract, self.SHORT_PUT, -1),
                self.SHORT_CALL: PositionLeg(short_call_contract, self.SHORT_CALL, -1),
                self.LONG_CALL: PositionLeg(long_call_contract, self.LONG_CALL, 1),
            }
        elif order_type == "LONG":
            self.legs = {
                self.LONG_PUT: PositionLeg(long_put_contract, self.LONG_PUT, -1),
                self.SHORT_PUT: PositionLeg(short_put_contract, self.SHORT_PUT, 1),
                self.SHORT_CALL: PositionLeg(short_call_contract, self.SHORT_CALL, 1),
                self.LONG_CALL: PositionLeg(long_call_contract, self.LONG_CALL, -1),
            }
    
    def get_long_put(self) -> PositionLeg:
        return self.legs[self.LONG_PUT]
    
    def get_long_call(self) -> PositionLeg:
        return self.legs[self.LONG_CALL]

    def get_short_put(self) -> PositionLeg:
        return self.legs[self.SHORT_PUT]
    
    def get_short_call(self) -> PositionLeg:
        return self.legs[self.SHORT_CALL]

    def all_filled(self):
        return all(leg.is_filled() for leg in self.legs.values())
    
    def get_avg_fill_price(self):
        prices = [leg.get_order_fill_price() for leg in self.legs.values()]
        return sum(prices) / len(prices)
    
    def get_total_fill_price(self):
        prices = [leg.get_order_fill_price() * leg.sign_multiplier for leg in self.legs.values()]
        return sum(prices)

    def get_leg_prices(self):
        return {
            'short_put': self.get_short_put().get_contract_prices(),
            'short_call': self.get_short_call().get_contract_prices(),
            'long_put': self.get_long_put().get_contract_prices(),
            'long_call': self.get_long_call().get_contract_prices(),
        }

    def get_sell_prices(self):
        pos_prices = self.get_leg_prices()
        short_put = pos_prices['short_put']
        short_call = pos_prices['short_call']
        long_put = pos_prices['long_put']
        long_call = pos_prices['long_call']

        bid = short_put['bid'] + short_call['bid'] + long_put['ask'] + long_call['ask']
        ask = short_put['ask'] + short_call['ask'] + long_put['bid'] + long_call['bid']
        mid = (bid + ask) / 2
        return {
            "bid":bid * 100, "ask": ask * 100, "mid": mid * 100
        }

        
    def get_buy_prices(self):
        pos_prices = self.get_leg_prices()
        short_put = pos_prices['short_put']
        short_call = pos_prices['short_call']
        long_put = pos_prices['long_put']
        long_call = pos_prices['long_call']
        ask = short_put['ask'] + short_call['ask'] + long_put['bid'] + long_call['bid']
        bid = (short_put['bid'] + short_call['bid'] + long_put['ask'] + long_call['ask'])
        mid = (bid + ask) / 2
        return {
            "bid":bid * 100, "ask": ask * 100, "mid": mid * 100
        }


    def set_fill_price(self, symbol, fill_price):
        if self.get_short_put().equals_symbol(symbol):
            self.get_short_put().fill_price = fill_price
        elif self.get_short_call().equals_symbol(symbol):
            self.get_short_call().fill_price = fill_price
        elif self.get_long_put().equals_symbol(symbol):
            self.get_long_put().fill_price = fill_price
        elif self.get_long_call().equals_symbol(symbol):
            self.get_long_call().fill_price = fill_price

    def to_dict(self):
        return {
            'long_put': f'{self.get_long_put().to_dict()}',
            'short_put': f'{self.get_short_put().to_dict()}',
            'short_call': f'{self.get_short_call().to_dict()}',
            'long_call': f'{self.get_long_call().to_dict()}'
        }

    def get_put_credit(self):
        # credit_put = short_put_bid − long_put_ask
        short_put_bid = self.get_short_put().contract.bid_price
        long_put_ask = self.get_long_put().contract.ask_price
        return short_put_bid - long_put_ask

    def get_call_credit(self):
        # credit_call = short_call_bid − long_call_ask
        short_call_bid = self.get_short_call().contract.bid_price
        long_call_ask = self.get_long_call().contract.ask_price
        return short_call_bid - long_call_ask
    
    def get_total_credit_estimate(self):
        # This is what you collect up front.
        # total_credit = credit_call + credit_put
        return self.get_call_credit() + self.get_put_credit()

# call_width = long_call_strike − short_call_strike
# put_width = short_put_strike − long_put_strike
# worst_width = max(call_width, put_width) (worst-case side)
    def get_put_width(self):
        short_put_strike = self.get_short_put().strike
        long_put_strike = self.get_long_put().strike
        return short_put_strike - long_put_strike
    
    def get_call_width(self):
        short_call_strike = self.get_short_call().strike
        long_call_strike = self.get_long_call().strike
        return short_call_strike - long_call_strike
    
    def get_credit_ratio(self):
        # “How much of the risk container am I being paid for?”
        # credit_ratio = total_credit / worst_width
        # worst_width = max(call_width, put_width)
        total_credit = self.get_total_credit_estimate()
        # worst_width This is the maximum gross risk per share before premium.
        worst_width = max(self.get_call_width(), self.get_put_width())
        credit_ratio = total_credit / worst_width
        return credit_ratio
        # require credit_ratio >= 0.25 (or 0.30 if you want stricter)
    
    def get_estimated_max_loss(self):
        # max_loss = worst_width − total_credit
        worst_width = max(self.get_call_width(), self.get_put_width())
        total_credit = self.get_total_credit_estimate()
        # return max(0.0, worst_width - total_credit)
            # add guard against slippage, inverted quotes, bad data
        return worst_width - total_credit

    # Two spreads can have the same max loss but very different quality.
    # Example A (good)
    # Width = 5.00
    # Credit = 1.75
    # Credit ratio = 35%
    # Max loss = 3.25

    # Example B (bad)
    # Width = 5.00
    # Credit = 0.60
    # Credit ratio = 12%
    # Max loss = 4.40
    
    # Both risk ~$500 per side, but:
    # A pays you well for risk
    # B pays you almost nothing
    # Credit ratio captures this pricing quality.
    
    
class IronCondorPosition:
    SHORT_PUT = "SHORT_PUT"
    SHORT_CALL = "SHORT_CALL"
    LONG_PUT = "LONG_PUT"
    LONG_CALL = "LONG_CALL"

    def __init__(self, symbol, long_put: OptionContract, short_put: OptionContract, short_call: OptionContract, long_call: OptionContract):
        self.total_legs = 4
        self.opening_legs = None
        self.closing_legs = None
        self.status: PositionStatus = PositionStatus.NONE
        self.symbol = symbol
        self.name = 'IRON_CONDOR'
        self.underlying_at_sell = None
        self.underlying_at_buy = None
        self.exit_reason = None
        self.entry_time = None
        self.exit_time = None
        

        self.set_opening_legs("SHORT", long_put, short_put, short_call, long_call)

    def set_opening_legs(self, order_type, long_put, short_put, short_call, long_call):
        self.opening_legs = IronCondorLegs(order_type, long_put, short_put, short_call, long_call)
    
    def set_closing_legs(self, legs: IronCondorLegs):
        self.closing_legs = legs
        
    def get_opening_legs(self) -> IronCondorLegs:
        return self.opening_legs
 
# can also do this
# legs = [
#     Leg.create(far_put.symbol, -1),
#     Leg.create(near_put.symbol, 1),
#     Leg.create(far_call.symbol, -1),
#     Leg.create(near_call.symbol, 1)
# ]
# self.combo_market_order(legs, 1)

    def get_qc_strategy(self, order_type) -> OptionStrategy:
        if order_type == "OPEN":
            legs = self.opening_legs
        elif order_type == "CLOSE":
            legs = self.closing_legs
        
        short_put = legs.get_short_put()
        iron_condor = OptionStrategies.short_iron_condor(
                short_put.symbol_canonical,
                legs.get_long_put().strike, 
                legs.get_short_put().strike, 
                legs.get_short_call().strike, 
                legs.get_long_call().strike,
                expiration=legs.get_short_put().expiry
        )
        return iron_condor
    
    def get_closing_qc_strategy(self) -> OptionStrategy:
        short_put = self.closing_legs.get_short_put()
        iron_condor = OptionStrategies.short_iron_condor(
            short_put.symbol_canonical,
            long_put_strike=self.opening_legs.get_long_put().strike,
            short_put_strike=self.opening_legs.get_short_put().strike,
            short_call_strike=self.opening_legs.get_short_call().strike,
            long_call_strike=self.opening_legs.get_long_call().strike,
            expiration=self.closing_legs.get_short_put().expiry
        )
        return iron_condor


    def get_opening_contracts(self):
        # [leg.contract for leg in self.opening_legs.values()]
        # contracts_by_leg = {
        #     k: v.contract
        #     for k, v in self.opening_legs.items()
        # }
        contracts = [c.contract for c in self.opening_legs.values()]
        return contracts

    def get_opening_order_tickets(self):
        orders = [c.order_ticket for c in self.opening_legs.values()]
        return orders

    def get_opening_avg_fill_price(self):
        return self.opening_legs.get_avg_fill_price()
    
    def get_opening_total_fill_price(self):
        return self.opening_legs.get_total_fill_price()
        
    def get_position_status(self) -> PositionStatus:
        return self.status
    
    def set_position_status(self, status: PositionStatus):
        self.status = status

    def get_opening_legs_json(self):
        json_string = json.dumps(self.opening_legs.to_dict())
        return json_string

    def get_opening_legs_strikes_json(self):
        json_string = {
            'long_put_strike': self.opening_legs.get_long_put().strike,
            'short_put_strike': self.opening_legs.get_short_put().strike,
            'short_call_strike': self.opening_legs.get_short_call().strike,
            'long_call_strike': self.opening_legs.get_long_call().strike
        }
        return json.dumps(json_string)              

    def get_closing_legs_strikes_json(self):
        json_string = {
            'long_put_strike': self.closing_legs.get_long_put().strike,
            'short_put_strike': self.closing_legs.get_short_put().strike,
            'short_call_strike': self.closing_legs.get_short_call().strike,
            'long_call_strike': self.closing_legs.get_long_call().strike
        }
        return json.dumps(json_string)   

    def get_entry_price(self):
        return self.closing_legs.get_total_fill_price()
    
    def get_exit_price(self):
        return self.opening_legs.get_total_fill_price()
        
    def get_exit_pnl(self):
        return abs(self.opening_legs.get_total_fill_price()) - self.closing_legs.get_total_fill_price()

    def get_exit_pnl_pct(self):
        o_fill = abs(self.opening_legs.get_total_fill_price())
        c_fill =  self.closing_legs.get_total_fill_price()
        pnl = o_fill - c_fill
        pnl_pct = ( pnl / o_fill ) * 100
        return pnl_pct
    

