
from research.models.trade_rule import TradeRule
class RuleSet:
    def __init__(self, rules: list[TradeRule]):
        self.rules = rules

    def evaluate(self, row: dict) -> tuple[bool, float]:
        """
        Returns:
        (allowed, final_size_multiplier)
        """
        size = 1.0

        for rule in self.rules:
            if rule.should_skip(row):
                return False, 0.0

            size *= rule.size_multiplier(row)

        return True, size
