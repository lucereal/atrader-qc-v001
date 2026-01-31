# region imports
from AlgorithmImports import *
from selection.iron_condor_scorer import IronCondorScorer
from selection.contract_selector import ContractSelector
from selection.option_chain_analyzer import OptionChainAnalyzer
from strategy.config import ContractSelectionConfig, IronCondorScoringConfig
from models import VerticalCandidate, IronCondorCandidate
from utils.position_finder_exception import PositionFinderException
from models.selection.scorer_result import ScorerResult, OptionChainFinderResult
from models.selection.finder_result import FinderResult
# endregion
class IronCondorScoreResult:
    def __init__(self, ic):
        self.ic = ic

class IronCondorFinder:
    def __init__(self, config, logger, contract_selector: ContractSelector, 
        iron_condor_scorer: IronCondorScorer, option_chain_analyzer: OptionChainAnalyzer):
        self.config = config
        self.logger = logger
        self.contract_selector = contract_selector
        self.iron_condor_scorer = iron_condor_scorer
        self.option_chain_analyzer = option_chain_analyzer


    def _get_valid_expiries(self, chain, now_time, sel_config):
        min_dte, max_dte = sel_config.dte_range
        all_expiries = self.option_chain_analyzer.get_all_expiries(chain)
        valid_expiries = set()
        for expiry in all_expiries:
            expiry_dte = self.dte_days_fractional(now_time, expiry)
            if min_dte <= expiry_dte <= max_dte:
                valid_expiries.add(expiry)
        return valid_expiries

    
    def find_best(self, now_time, symbol, underlying_price, chain, sel_config: ContractSelectionConfig) -> FinderResult:
        finder_result = FinderResult()
        try:
            valid_expiries = self._get_valid_expiries(chain, now_time, sel_config)
            
            all_score_results: list[ScorerResult] = []
            for expiry in valid_expiries:
                contract_candidates: OptionChainFinderResult = None
                if sel_config.is_use_fixed_delta:
                    contract_candidates = self.option_chain_analyzer.find_fixed_delta(
                        symbol, expiry, now_time, underlying_price, self.config.short_delta_fixed_target)
                else:
                    contract_candidates = self.option_chain_analyzer.find_candidates(
                        symbol, expiry, now_time, underlying_price)
                if contract_candidates and not contract_candidates.had_error and contract_candidates.is_calls_and_puts_not_empty():
                    contract_bundle: ContractSelectorResult = None
                    if sel_config.is_use_fixed_spread_width:
                        call_spreads, put_spreads = self.find_long_leg_with_fixed_width(contract_candidates.calls, contract_candidates.puts, symbol, expiry, sel_config.fixed_spread_width)
                        contract_bundle = self.contract_selector.select_vertical_spreads_fixed_width(
                            sel_config, call_spreads, put_spreads, symbol, expiry)
                    else:
                        contract_bundle = self.contract_selector.select_vertical_spreads(
                            sel_config, contract_candidates.calls, contract_candidates.puts)
                    if contract_bundle and not contract_bundle.had_error and contract_bundle.is_verticals_populated():
                        scorer_result = self.iron_condor_scorer.rank(contract_bundle.put_verticals, contract_bundle.call_verticals, underlying_price, contract_candidates.em)
                        finder_result.add_score_result(expiry,scorer_result)
        except Exception as e:
            finder_result.had_error = True
            finder_result.exception = e

        if not finder_result.has_found_result():
            finder_result.had_error = True
        return finder_result

    def find_long_leg_with_fixed_width(self, short_calls, short_puts, symbol, expiry, fixed_spread_width):
        call_spreads = {}
        for short_call in short_calls:
            longs = self.option_chain_analyzer.long_legs_for_short_fixed_width(symbol,
                short_call, expiry, fixed_spread_width, "call"
            )
            if longs:
                call_spreads[short_call] = longs

        put_spreads = {}
        for short_put in short_puts:
            longs = self.option_chain_analyzer.long_legs_for_short_fixed_width(symbol,
                short_put, expiry, fixed_spread_width, "put"
            )
            if longs:
                put_spreads[short_put] = longs
        return call_spreads, put_spreads

    def dte_days_fractional(self, now_time, expiry):
        # expiry is a datetime-like; treat expiration as 4:00pm local exchange time
        expiry_dt = expiry.replace(hour=16, minute=0, second=0, microsecond=0)
        seconds = (expiry_dt - now_time).total_seconds()
        return max(seconds / 86400.0, 0.0)
