class RuleCondition:
    """
    A single condition like:
    { time_bucket: '0-30', adx_bucket: '(25.0, 40.0]' }
    """

    def __init__(self, **kwargs):
        self.filters = kwargs  # raw dict
   
    def matches(self, row: dict, trace: bool = False):
        details = []

        for key, expected in self.filters.items():
            actual = row.get(key)
            ok = (actual == expected)

            if trace:
                details.append({
                    "key": key,
                    "expected": expected,
                    "actual": actual,
                    "actual_type": type(actual).__name__,
                    "ok": ok,
                })

            if not ok:
                return (False, details) if trace else False

        return (True, details) if trace else True
