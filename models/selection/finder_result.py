# region imports
from AlgorithmImports import *
from models import IronCondorCandidate, VerticalCandidate, ScorerResult
# endregion

class FinderResult:
    


    def __init__(self):
        self.results_by_expiry: dict[str, ScorerResult] = {}
        self.had_error: bool = False
        self.exception = None

    def has_found_result(self):
        if len(self.results_by_expiry.keys()) > 0:
            return True
        return False
    
    def get_best_ic_overall(self) -> IronCondorCandidate:
        return self.get_best_of_all().best_overall

    def get_best_by_expiry(self, expiry):
        expiry_str = expiry.date().strftime("%Y-%m-%d")
        if expiry_str in self.results_by_expiry:
            return self.results_by_expiry[expiry_str]
        return None

    def get_best_of_all(self) -> ScorerResult:
        best = max(
            self.results_by_expiry.values(),
            key=lambda r: r.get_best_overall_score(),
            default=None
        )
        return best

    def add_score_result(self, expiry, score_result: ScorerResult):
        expiry_str = expiry.date().strftime("%Y-%m-%d")
        if expiry_str not in self.results_by_expiry:
            self.results_by_expiry[expiry_str] = score_result


class ContractSelectorResult:

    def __init__(self):
        self.call_verticals: list[VerticalCandidate] = []
        self.put_verticals: list[VerticalCandidate] = []
        self.had_error: bool = False
        self.exception = None

    def is_verticals_populated(self):
        return len(self.call_verticals) > 0 and len(self.put_verticals) > 0
