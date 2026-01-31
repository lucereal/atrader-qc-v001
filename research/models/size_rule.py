from research.models.rule_condition import RuleCondition

class SizeRule(RuleCondition):
    """
    Same as RuleCondition, but with a multiplier
    """

    def __init__(self, mult: float, **kwargs):
        super().__init__(**kwargs)
        self.mult = mult
