# region imports
from AlgorithmImports import *
from analytics.option_metrics import OptionMetrics
from utils.position_finder_exception import PositionFinderException
from models.selection.scorer_result import ScorerResult
from models.candidates import IronCondorCandidate
# endregion

class IronCondorScorer:
    def __init__(self, config):
        self.config = config

    def get_scores(self, ic: IronCondorCandidate, underlying_price):
        center = self.get_center_score(ic.put,ic.call,underlying_price, self.config.missing_centering_score, self.config.check_center_score)
        balance = self.get_delta_balance_score(ic.put, ic.call, self.config.missing_delta_score, self.config.check_delta_balance)

        ic.rr_score = self.config.w_rr * ic.rr
        ic.cushion_score = self.config.w_cushion * ic.cushion
        ic.center_score = self.config.w_center * center['score']
        ic.delta_balance_score = self.config.w_balance * balance['score']
        
        score = (
            self.config.w_rr * ic.rr +
            self.config.w_cushion * ic.cushion +
            self.config.w_center * center['score'] +
            self.config.w_balance * balance['score']
        )
        ic.overall_score = score
     
    def run_checks(self, ic):
        is_risk_defined = self.check_is_defined_risk(pv, cv, underlying_price)
        em_and_max_loss = self.check_em_and_max_loss(ic)
    
        ic.defined_risk = is_risk_defined["check_passed"]
        ic.data["is_risk_defined"] = is_risk_defined
        ic.data["em_and_max_loss"] = em_and_max_loss

        rr = self.check_rr(ic, self.config.min_rr)
        ic.data["check_rr"] = rr
        

    def rank(self, put_verticals, call_verticals, underlying_price, expected_move) -> ScorerResult:
        result = ScorerResult()
        try:
            for pv in put_verticals:
                for cv in call_verticals:
                    ic = OptionMetrics.iron_condor_candidate(
                        pv, cv, underlying_price, expected_move, em_buffer=self.config.em_buffer
                    )
                    self.get_scores(ic, underlying_price)
                    result.add_candidate(ic)          
        except Exception as e:
            result.had_error = True
            result.exception = pe
        return result

    def check_rr(self, ic, min_rr):
        result = {
            "check_passed": False
        }
        try:
            result["rule"] = "ic.rr < min_rr"
            result["data"] = {
                "rr": ic.rr, "min_rr": min_rr
            }
            if ic.rr < min_rr:
                result["check_passed"] = False
            else:
                result["check_passed"] = True
        except Exception as e:
            ex_rf = {"pv":pv,"cv":cv,"und_p": underlying_price, "em":expected_move, 
                "ic.rr":ic.rr, "config.min_rr": min_rr}
            raise PositionFinderException("iron_condor_position.check_rr: OptionMetrics had an exception", ex_rf)
        return result

    def check_em_and_max_loss(self, ic):
        result = {
            "check_passed": False
        }
        try:
            result["rule"] = "ic.em_ok or ic.max_loss <= 0"
            result["data"] = {
                "em_ok": ic.em_ok, "max_loss": ic.max_loss
            }
            if not ic.em_ok or ic.max_loss <= 0:
                result["check_passed"] = False
            else:
                result["check_passed"] = True
        except Exception as e:
            ex_rf = {"pv":pv,"cv":cv,"und_p": underlying_price, "em":expected_move, 
                "ic_em":ic.em_ok, "ic.max_loss": ic.max_loss}
            raise PositionFinderException("iron_condor_position.is_defined_risk: OptionMetrics had an exception", ex_rf)
        return result
                
    def check_is_defined_risk(self, pv, cv, underlying_price, require_brackets_spot=True):
        result = {
            "rule_name": "is_defined_risk",
            "check_passed": False
        }
        try:
            is_defined_risk = OptionMetrics._is_defined_risk(pv, cv, underlying_price, require_brackets_spot=require_brackets_spot)
            if not is_defined_risk:
                ex_rf = {"pv":pv,"cv":cv,"und_p": underlying_price, "em":expected_move, "is_defined_risk": is_defined_risk}
                raise PositionFinderException(
                    "iron_condor_position.is_defined_risk: is_defined_risk is None", 
                    ex_rf)
            result["rule"] = "is_defined_risk = true"
            result["data"] = {
                "is_defined_risk": is_defined_risk
            }
            result["check_passed"] = True
        except Exception as e:
            ex_rf = {"pv":pv,"cv":cv,"und_p": underlying_price, "em":expected_move}
            raise PositionFinderException(
                "iron_condor_position.is_defined_risk: OptionMetrics threw an exception", 
                ex_rf) from e
        return result


    def get_delta_balance_score(self, pv, cv, underlying_price, missing_delta_score, check_delta_balance=True):
        result = {
            "score_name": "check_delta_balance",
            "score": missing_delta_score,
            "score_retrieved": False,
            "missing_delta_score": missing_delta_score,
            "check_delta_balance": check_delta_balance,
            "data": {}
        }
        if not check_delta_balance:
            return result
        try:
            balance = OptionMetrics._ic_delta_balance_score(pv, cv, missing_score=missing_delta_score)
            result["data"]["balance"] = balance
            result["score_retrieved"] = True
            result["score"] = balance
            
        except Exception as e:
            ex_rf = {"pv":pv,"cv":cv,"und_p": underlying_price, "balance": balance, "missing_delta_score": missing_delta_score}
            raise PositionFinderException(
                "iron_condor_position.get_delta_balance_score: OptionMetrics threw an exception", 
                ex_rf) from e
        return result
               
    def get_center_score(self, pv, cv, underlying_price, missing_centering_score, check_center_score = True):
        result = {
            "score_name": "check_delta_balance",
            "score": missing_centering_score,
            "score_retrieved": False,
            "missing_centering_score": missing_centering_score,
            "check_center_score": check_center_score,
            "data": {}
        }

        if not check_center_score:
            return result
        
        try:
            center = OptionMetrics._ic_centering_score(pv, cv, underlying_price)
            result["data"]["center"] = center
            result["score_retrieved"] = True
            result["score"] = center
            
        except Exception as e:
            ex_rf = {"pv":pv,"cv":cv,"und_p": underlying_price, "center": center}
            raise PositionFinderException(
                "iron_condor_position.get_center_score: OptionMetrics threw an exception", 
                ex_rf) from e
        return result     


    # should only need this for pruning if I have a large number of puts and calls to rank in the IC condor scoring
    def _filter_and_rank_verticals(verticals, min_credit, min_ratio, top_n):
        v = [
            x for x in verticals
            if x.credit >= min_credit and x.credit_ratio >= min_ratio and x.width > 0
        ]
        v.sort(key=lambda x: (x.credit_ratio, x.credit), reverse=True)
        return v[:top_n]
