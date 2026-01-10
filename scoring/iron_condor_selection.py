# region imports
from AlgorithmImports import *
# endregion

class IronCondorScorer:
    def __init__(self, config):
        self.config = config

    def rank(self, put_verticals, call_verticals, underlying_price, expected_move):
        candidates = []
        for pv in put_verticals:
            for cv in call_verticals:
                if not OptionMetrics._is_defined_risk(pv, cv, underlying_price, require_brackets_spot=True):
                    continue

                ic = OptionMetrics.iron_condor_candidate(
                    pv, cv, underlying_price, expected_move, em_buffer=self.config.em_buffer
                )

                if not ic.em_ok or ic.max_loss <= 0:
                    continue
                if ic.rr < self.config.min_rr:
                    continue

                center = OptionMetrics._ic_centering_score(pv, cv, underlying_price)
                balance = OptionMetrics._ic_delta_balance_score(pv, cv, missing_score=0.5)

                score = (
                    self.config.w_rr * ic.rr +
                    self.config.w_cushion * ic.cushion +
                    self.config.w_center * center +
                    self.config.w_balance * balance
                )
                candidates.append((score, ic))

        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates
