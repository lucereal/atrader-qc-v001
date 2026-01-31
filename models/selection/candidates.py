
# region imports
from dataclasses import dataclass
from typing import Any, Optional
# endregion
  
class VerticalCandidate:
    def __init__(self, side, short, long, width, credit, credit_ratio, short_delta, long_delta):
        self.side: str = side              
        self.short: OptionContract = short            
        self.long: OptionContract = long               
        self.width: float = width
        self.credit: float = credit
        self.credit_ratio: float = credit_ratio
        self.short_delta: Optional[float] = short_delta
        self.long_delta: Optional[float] = long_delta

    def to_dict(self):
        return {
            "side": self.side,
            "width": self.width,
            "credit": self.credit,
            "credit_ratio": self.credit_ratio,
            "short": self.to_dict_contract("short"),
            "long": self.to_dict_contract("long")
        }

    def to_dict_contract(self, direction):
        c: OptionContract = self.long
        if direction == "short":
            c = self.short
    
        return {
            "symbol": c.symbol.value,
            "strike": c.strike,
            "iv": c.implied_volatility,
            "oi": c.open_interest,
            "volume": c.volume,
            "expiry": c.expiry.strftime("%Y-%m-%d, %H:%M:%S"),
            "delta": c.greeks.delta,
            "gamma": c.greeks.gamma,
            "theta": c.greeks.theta,
            "vega": c.greeks.vega,
            "theta_per_day": c.greeks.theta_per_day,
            "ask_size": c.ask_size,
            "ask_price": c.ask_price,
            "bid_size": c.bid_size,
            "bid_price": c.bid_price,
            "last_price": c.last_price

        }
    

class IronCondorCandidate:
    def __init__(self, put, call, total_credit, max_loss, rr, em_ok, cushion, em):
        self.put: VerticalCandidate = put
        self.call: VerticalCandidate = call
        self.total_credit: float = total_credit
        self.max_loss: float = max_loss
        self.rr: float = rr                        
        self.em_ok: bool = em_ok
        self.em: float = em
        self.cushion: Optional[float] = cushion                   
        self.defined_risk: Optional[bool] = None
        self.cushion_score: Optional[bool] = 0.0
        self.rr_score: Optional[float] = 0.0 
        self.center_score: Optional[float] = 0.0
        self.delta_balance_score: Optional[float] = 0.0
        self.overall_score: Optional[float] = 0.0

    def get_expiry(self):
        return self.put.short.expiry

    def to_dict(self):
        return {
            "put": self.put.to_dict(),
            "call": self.call.to_dict(),
            "total_credit": self.total_credit,
            "max_loss": self.max_loss,
            "rr": self.rr,
            "em": self.em,
            "em_ok": self.em_ok,
            "cushion": self.cushion,
            "defined_risk": self.defined_risk,
            "cushion_score": self.cushion_score,
            "rr_score": self.rr_score,
            "center_score": self.center_score,
            "delta_balance_score": self.delta_balance_score,
            "overall_score": self.overall_score
        }
    def _to_dict(self):
        return {
            "put": put, "call": call, "total_credit": total_credit,
            "max_loss": max_loss, "rr": rr, "em_ok": em_ok
        }
    
    def set_defined_risk(self, defined_risk):
        self.data["defined_risk"] = defined_risk
        self.defined_risk = defined_risk["check_passed"]


class ScoredIronCondor:
    def __init__(self):
        self.ic: IronCondorCandidate = None
        self.defined_risk: Optional[bool] = None
        self.centering: Optional[float] = None
        self.delta_balance: Optional[float] = None
        self.score: Optional[float] = None
