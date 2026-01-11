# region imports
from AlgorithmImports import *
from models import PositionOrderStatus, IronCondorLegs, PositionLeg
import json
# endregion


    
class IronCondorPosition:
    SHORT_PUT = "SHORT_PUT"
    SHORT_CALL = "SHORT_CALL"
    LONG_PUT = "LONG_PUT"
    LONG_CALL = "LONG_CALL"

    def __init__(self, symbol, long_put: OptionContract, short_put: OptionContract, short_call: OptionContract, long_call: OptionContract):
        import uuid
        self.trade_id = uuid.uuid4().hex   # 32-char string
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
        self.ic_candidate = None
        self.technicals = None
        self.set_opening_legs("SHORT", long_put, short_put, short_call, long_call)


    def to_dict(self):
        import json
        return {
            "symbol": str(self.symbol),
            "strategy": "IRON_CONDOR",
            "status": self.status,
            "total_legs": self.total_legs,
            "underlying_at_entry": self.underlying_at_buy,
            "underlying_at_exit": self.underlying_at_sell,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "exit_reason": self.exit_reason,
            "opening_legs": self.opening_legs.to_dict(),
            "closing_legs": self.closing_legs.to_dict(), 
            "technicals": self.technicals
        }
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
        open_cash = self.opening_legs.get_total_cashflow() 
        close_cash = self.closing_legs.get_total_cashflow()
        return open_cash + close_cash

    def get_exit_pnl_pct(self):
        o_fill = abs(self.opening_legs.get_total_fill_price())
        c_fill =  self.closing_legs.get_total_fill_price()
        pnl = o_fill - c_fill
        pnl_pct = ( pnl / o_fill ) * 100
        return pnl_pct
    

