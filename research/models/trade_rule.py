from research.models.size_rule import SizeRule
from research.models.rule_condition import RuleCondition

class TradeRule:
    def __init__(self, name: str, skip: list, size: list):
        self.name = name
        self.skip_rules: list[RuleCondition] = skip
        self.size_rules: list[SizeRule] = size

    def should_skip(self, row: dict, trace: bool = False):
        """
        Returns:
        trace=False -> bool
        trace=True  -> (bool, trace_dict | None)
        """
        for cond in self.skip_rules:
            if trace:
                ok, details = cond.matches(row, trace=True)
                if ok:
                    return True, {
                        "rule": self.name,
                        "action": "SKIP",
                        "checks": details,
                    }
            else:
                if cond.matches(row, trace=False):
                    return True

        return (False, None) if trace else False

    def size_multiplier(self, row: dict, trace: bool = False):
        """
        Returns:
        trace=False -> float
        trace=True  -> (float, trace_dict | None)
        """
        for cond in self.size_rules:
            if trace:
                ok, details = cond.matches(row, trace=True)
                if ok:
                    return cond.mult, {
                        "rule": self.name,
                        "action": "SIZE",
                        "mult": cond.mult,
                        "checks": details,
                    }
            else:
                if cond.matches(row, trace=False):
                    return cond.mult

        return (1.0, None) if trace else 1.0
