# region imports
from AlgorithmImports import *
from research.condor_research import CondorResearch
from research.models.rule_set import RuleSet
from research.models.size_rule import SizeRule
from research.models.rule_condition import RuleCondition
from research.models.trade_rule import TradeRule
# endregion

# Your New Python File
class CondorFantasy:
    def __init__(self, cr: CondorResearch, rules: list[dict], cfg=None):
        self.cfg = cfg  
        self.cr = cr
        self.ruleset = self._load_trade_rules(rules)
        self._normalize_buckets()
        self.df = cr.df.copy()
            
    def _load_trade_rules(self, raw_rules: list[dict]) -> RuleSet:
        rules_out = []
        for r in raw_rules:
            skip_rules = [RuleCondition(**cond) for cond in r.get("skip", [])]

            size_rules = []
            for cond in r.get("size", []):
                if "mult" not in cond:
                    raise ValueError(f"Size rule missing 'mult' in {r['name']}: {cond}")
                mult = cond["mult"]
                filters = {k: v for k, v in cond.items() if k != "mult"}
                size_rules.append(SizeRule(mult=mult, **filters))

            rules_out.append(TradeRule(name=r["name"], skip=skip_rules, size=size_rules))

        return RuleSet(rules_out)

    def evaluate_row(self, row: dict, trace: bool = False):
        allowed = True
        size = 1.0
        rule_results = []

        for rule in self.ruleset.rules:
            rule_entry = {
                "rule": rule.name,
                "skip": None,
                "size": None,
            }

            # --- SKIP ---
            if trace:
                is_skip, skip_trace = rule.should_skip(row, trace=True)
                rule_entry["skip"] = {
                    "matched": is_skip,
                    "checks": skip_trace["checks"] if skip_trace else [],
                }
                if is_skip:
                    allowed = False
            else:
                is_skip = rule.should_skip(row, trace=False)
                rule_entry["skip"] = {"matched": is_skip}
                if is_skip:
                    allowed = False

            # --- SIZE ---
            if trace:
                mult, size_trace = rule.size_multiplier(row, trace=True)
                rule_entry["size"] = {
                    "matched": size_trace is not None,
                    "mult": mult,
                    "checks": size_trace["checks"] if size_trace else [],
                }
                if allowed:
                    size *= mult
            else:
                mult = rule.size_multiplier(row, trace=False)
                rule_entry["size"] = {"matched": mult != 1.0, "mult": mult}
                if allowed:
                    size *= mult

            rule_results.append(rule_entry)

        return {
            "allowed": allowed,
            "size_mult": (size if allowed else 0.0),
            "rules": rule_results,
        }


    def _normalize_buckets(self):
        bucket_cols = [c for c in self.cr.df.columns if c.endswith("_bucket")]
        for c in bucket_cols:
            self.cr.df[c] = self.cr.df[c].apply(lambda v: str(v) if isinstance(v, pd.Interval) else v)


# import json
# from pathlib import Path
# import numpy as np
# import pandas as pd

# class CondorFantasy:
#     """
#     Apply rule sets (skip + sizing) to a CondorResearch dataframe and
#     compute counterfactual PnL/stats.
#     """

#     def __init__(self, df: pd.DataFrame, cr, rules, cfg=None):
#         self.cfg = cfg
#         self.df = df.copy()
#         self.cr = cr
#         self.rules = self._load_rules(rules)

#         # outputs
#         self.df_ruled: pd.DataFrame | None = None

#     # ----------------------------
#     # Rules I/O
#     # ----------------------------
#     def _load_rules(self, rules):
#         # dict already
#         if isinstance(rules, dict):
#             return rules

#         # allow Path-like or filename
#         if isinstance(rules, (str, Path)):
#             p = Path(rules)
#             if p.exists():
#                 return json.loads(p.read_text())
#             # if user passed just a name, optionally resolve via cfg
#             if self.cfg and getattr(self.cfg, "rules_dir", None):
#                 p2 = Path(self.cfg.rules_dir) / rules
#                 if p2.exists():
#                     return json.loads(p2.read_text())
#             raise FileNotFoundError(f"Rules file not found: {rules}")

#         raise TypeError(f"Unsupported rules type: {type(rules)}")

#     def save_rules(self, path: str | Path):
#         path = Path(path)
#         path.write_text(json.dumps(self.rules, indent=2, sort_keys=True))

#     # ----------------------------
#     # Core: compile + apply
#     # ----------------------------
#     def _rule_to_mask(self, df: pd.DataFrame, cond: dict) -> pd.Series:
#         """
#         Build a boolean mask from a condition dict like:
#           {"time_bucket": "0-30", "adx_bucket": "(25.0, 40.0]"}
#         Supports:
#           - exact match: col: value
#           - list match: col: [v1, v2]
#           - in: {"col": {"in": [..]}}
#           - not_in: {"col": {"not_in": [..]}}
#         """
#         mask = pd.Series(True, index=df.index)

#         for col, spec in cond.items():
#             if isinstance(spec, dict):
#                 if "in" in spec:
#                     mask &= df[col].isin(spec["in"])
#                 elif "not_in" in spec:
#                     mask &= ~df[col].isin(spec["not_in"])
#                 else:
#                     raise ValueError(f"Unknown operator in {spec} for col {col}")
#             elif isinstance(spec, list):
#                 mask &= df[col].isin(spec)
#             else:
#                 mask &= (df[col] == spec)

#         return mask

#     def apply(self, pnl_col: str = "pnl", out_col: str = "pnl_ruled") -> pd.DataFrame:
#         """
#         Applies rules to self.df, producing rule_skip, rule_mult, pnl_ruled.
#         Returns the modified df.
#         """
#         df = self.df.copy()

#         # base columns
#         df["rule_skip"] = False
#         df["rule_mult"] = 1.0

#         # ---- SKIP ----
#         for r in self.rules.get("skip", []):
#             cond = r.get("when", r)  # support {"when": {...}} or direct dict
#             mask = self._rule_to_mask(df, cond)
#             df.loc[mask, "rule_skip"] = True

#         # ---- SIZE ----
#         for r in self.rules.get("size", []):
#             mult = float(r["mult"])
#             cond = r.get("when", {k: v for k, v in r.items() if k != "mult"})
#             mask = self._rule_to_mask(df, cond)
#             df.loc[mask, "rule_mult"] = mult

#         # skipped trades get 0 sizing
#         df.loc[df["rule_skip"], "rule_mult"] = 0.0

#         # ruled pnl
#         df[out_col] = df[pnl_col] * df["rule_mult"]

#         self.df_ruled = df
#         return df

#     # ----------------------------
#     # Stats helpers
#     # ----------------------------
#     def total_pnl(self, col: str = "pnl_ruled") -> float:
#         if self.df_ruled is None:
#             raise RuntimeError("Call apply() first.")
#         return float(self.df_ruled[col].sum())

#     def trade_count(self, include_skipped: bool = False) -> int:
#         if self.df_ruled is None:
#             raise RuntimeError("Call apply() first.")
#         if include_skipped:
#             return int(len(self.df_ruled))
#         return int((self.df_ruled["rule_mult"] > 0).sum())

#     def stats(self, keys, value_col: str = "pnl_ruled", include_expectancy: bool = False):
#         """
#         Reuse CondorResearch.group_stats by temporarily swapping its df.
#         Keeps your CR unchanged long-term.
#         """
#         if self.df_ruled is None:
#             raise RuntimeError("Call apply() first.")

#         old_df = self.cr.df
#         try:
#             self.cr.df = self.df_ruled
#             return self.cr.group_stats(keys=keys, value_col=value_col, include_expectancy=include_expectancy)
#         finally:
#             self.cr.df = old_df
