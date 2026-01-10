import pandas as pd
import numpy as np
from research.research_utils import (
    get_latest_trade_analytics_key,
    expectancy
)


class CondorResearch:
    def __init__(self, df: pd.DataFrame, cfg=None):
        self.cfg = cfg  
        self.df = df.copy()
        self.prepare()


    def prepare(self):
        self.df["pnl"] = self.df["pos.pnl"].astype(float)
        self.df["abs_pnl"] = self.df["pnl"].abs()
        self.df["win"] = self.df["pnl"] > 0
        self.df["loss"] = self.df["pnl"] <= 0
        self.df["is_win"] = self.df["pos.pnl"] > 0
        self._prepare_entry_exit_stats()

    def get_win_rate(self):
        num_positions = self.df.shape[0]
        num_wins = self.df["is_win"].sum()
        num_losses = (~df["is_win"]).sum()
        win_rate = num_wins / num_positions
        return win_rate

    def get_num_0_pnl(self):
        eps = 1e-6
        num_0_pnl = (df["pos.pnl"].abs() < eps).sum()
        return num_0_pnl

    def get_total_pnl(self):
        return 100 * self.df["pnl"].sum()

    def entry_exit_stats_group(self, view: str = "tidy", grid_value: str = None):
        bucket = self.add_bucket(
            source_col="entry_minutes_since_open",
            bins=self.cfg.time_bins,
            name="time_bucket"
        )
        tidy = self.group_stats(keys=["time_bucket"], value_col="pnl", include_expectancy=False)
        if view == "multi":
            return self.as_multiindex(tidy, keys=["time_bucket"], cols=["count","mean","win_rate","tail_ratio_q05","expectancy","low_confidence"])
        if view == "grid" and grid_value:
            return self.grid(tidy, index="time_bucket", columns="adx_bucket", values=grid_value)
        return tidy

    def time_and_adx_stats(self, view: str = "tidy", grid_value: str = None):
        time_bucket = self.add_bucket(
            source_col="entry_minutes_since_open",
            bins=self.cfg.time_bins,
            name="time_bucket"
        )
        adx_bucket = self.add_bucket(
            source_col="pos.position.technicals.current_adx",
            bins=self.cfg.adx_bins,
            name="adx_bucket"
        )
        tidy = self.group_stats(keys=["time_bucket", "adx_bucket"], value_col="pnl",
            include_expectancy=False)
        if view == "multi":
            return self.as_multiindex(tidy, keys=["time_bucket", "adx_bucket"], cols=["count","mean","win_rate","tail_ratio_q05","expectancy","low_confidence"])
        if view == "grid" and grid_value:
            return self.grid(tidy, index="time_bucket", columns="adx_bucket", values=grid_value)
        return tidy

    def add_bucket(self, source_col: str, bins, name: str | None = None, labels = None, 
        include_lowest: bool = True, right: bool = True) -> str:
        bucket_col = name or f"{source_col}_bucket"
        self.df[bucket_col] = pd.cut(
            self.df[source_col],
            bins=bins,
            labels=labels,
            include_lowest=include_lowest,
            right=right
        )
        return bucket_col

    def group_stats(self, keys: list[str], value_col: str = "pnl", q_low=(0.01, 0.05), q_high=(0.95,),
            include_expectancy: bool = True, min_count: int = 20, eps_mean: float = 1e-12, 
            add_tail_ratios: bool = True, add_upside_ratios: bool = False,
            win_threshold: float = 0.0, zero_is_loss: bool = True,
        ) -> pd.DataFrame:
        """
        Compute stats over any number of grouping keys (bucket columns or categorical columns).
        Returns a tidy DataFrame (one row per group).
        - this gives stats per bucket group, not per trade
        - you will get one row per group like - time_bucket, time_bucket+adx_bucket, time_bucket+adx_bucket+dte_bucket
        - this is the aggregated summary

        """
        def q(p): return lambda x: x.quantile(p)
        agg = {
            "count": "count",
            "mean": "mean",
            "std": "std",
            "min": "min",
        }
        for p in q_low:
            agg[f"q{int(p*100):02d}"] = q(p)
        agg["median"] = "median"
        for p in q_high:
            agg[f"q{int(p*100):02d}"] = q(p)
        agg["max"] = "max"
        g = self.df.groupby(keys, dropna=False)[value_col] 
        out = g.agg(**agg).reset_index()
        wl = g.apply(lambda s: self._wl_stats(s, win_threshold, zero_is_loss)).unstack().reset_index()
        out = out.merge(wl, on=keys, how="left")
        out["low_confidence"] = out["count"] < min_count
        denom = out["mean"].abs().clip(lower=eps_mean)
        if add_tail_ratios:
            for p in q_low:
                qname = f"q{int(p*100):02d}"
                if qname in out.columns:
                    out[f"tail_ratio_{qname}"] = out[qname].abs() / denom

        if add_upside_ratios:
            for p in q_high:
                qname = f"q{int(p*100):02d}"
                if qname in out.columns:
                    out[f"upside_ratio_{qname}"] = out[qname].abs() / denom
        return out.sort_values("count", ascending=False).reset_index(drop=True)

    def _wl_stats(self, x: pd.Series, win_threshold: float = 0.0, zero_is_loss: bool = True,
        include_expectancy: bool = True) -> pd.Series:
        x = x.dropna()
        if len(x) == 0:
            return pd.Series(
                {"win_rate": np.nan, "avg_win": np.nan, "avg_loss": np.nan, "expectancy": np.nan}
            )

        is_win = x > win_threshold
        if zero_is_loss:
            is_loss = ~is_win  # includes zeros and negatives
        else:
            is_loss = x < win_threshold  # excludes exact zeros if win_threshold==0

        win_rate = is_win.mean()
        avg_win = x[is_win].mean() if is_win.any() else np.nan
        avg_loss = x[is_loss].mean() if is_loss.any() else np.nan
        exp = win_rate * avg_win + (1 - win_rate) * avg_loss

        return pd.Series({"win_rate": win_rate, "avg_win": avg_win, "avg_loss": avg_loss, "expectancy": exp})

    @staticmethod
    def pivot_view(tidy: pd.DataFrame, index: str, columns: str, values: str):
        return tidy.pivot_table(index=index, columns=columns, values=values, aggfunc="first")

    def as_multiindex(self, tidy: pd.DataFrame, keys: list[str], cols=None) -> pd.DataFrame:
        cols = cols or [c for c in tidy.columns if c not in keys]
        return tidy.set_index(keys).sort_index()[cols]

    def grid(self, tidy: pd.DataFrame, index: str, columns: str, values: str) -> pd.DataFrame:
        return tidy.pivot_table(index=index, columns=columns, values=values, aggfunc="first")

    def _prepare_entry_exit_stats(self):
        self.df["pos.entry"] = pd.to_datetime(self.df["pos.position.entry_time"], errors="coerce")
        self.df["pos.exit"] = pd.to_datetime(self.df["pos.position.exit_time"], errors="coerce")
        self.df["entry_hour"] = self.df["pos.entry"].dt.hour
        self.df["entry_minute"] = self.df["pos.entry"].dt.minute
        self.df["entry_minutes_since_open"] = (
            self.df["entry_hour"] * 60 + self.df["entry_minute"]
        ) - (9 * 60 + 30)
        self.df["exit_hour"] = self.df["pos.exit"].dt.hour
        self.df["exit_minute"] = self.df["pos.exit"].dt.minute
        self.df["hold_minutes"] = (
            self.df["pos.exit"] - self.df["pos.entry"]
        ).dt.total_seconds() / 60
    
