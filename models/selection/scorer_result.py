# region imports
from AlgorithmImports import *
from .candidates import IronCondorCandidate
# endregion

class ScorerResult:

    def __init__(self):
        self.all_candidates: list[IronCondorCandidate] = []
        self.best_by_expiry: dict[str, list[IronCondorCandidate]] = {}
        self.best_overall: IronCondorCandidate = None
        self.had_error: bool = False
        self.exception = None

    def get_best_overall_score(self):
        return self.best_overall.overall_score
        
    def _add_best_overall(self, ic):
        if not self.best_overall or (ic.overall_score > self.best_overall.overall_score):
            self.best_overall = ic


    def add_candidate(self, ic: IronCondorCandidate):
        self.all_candidates.append(ic)
        self._add_best_overall(ic)

    def has_candidates(self):
        if len(self.all_candidates) > 0:
            return True
        return False

class OptionChainFinderResult:
    def __init__(self):
        self.calls = []
        self.puts = []
        self.iv = 0.0
        self.em = 0.0
        self.had_error: bool = False
        self.exception = None
    
    def is_calls_and_puts_not_empty(self):
        return len(self.calls) > 0 and len(self.puts) > 0

class RuleResult:
    def __init__(self):
        self.ruleResult: bool = False
        self.rule_type: str
        self.isSuccess: bool
        self.ruleDefinition: str
        self.data: dict

class ScoreData:
    def __init__(self):
        self.score_type: str
        self.score: float = None
        self.isSuccess: bool
        self.default: float = None
        self.data: dict
