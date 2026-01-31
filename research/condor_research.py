# region imports
from AlgorithmImports import *
# endregion
# region imports
import pandas as pd
import numpy as np
from research.research_utils import (
    get_latest_trade_analytics_key,
    expectancy
)
# endregion

class CondorResearch:
    def __init__(self, df: pd.DataFrame, cfg=None):
        self.cfg = cfg  
        self.df = df.copy()
        self.prepare()
        self.total_trades = None
        self.total_unq_trade_ids = None


    def prepare(self):
        self.df["pnl"] = self.df["pos.pnl"].astype(float)
        self.df["abs_pnl"] = self.df["pnl"].abs()
        self.df["win"] = self.df["pnl"] > 0
        self.df["loss"] = self.df["pnl"] <= 0
        self.df["is_win"] = self.df["pos.pnl"] > 0
        
        # self.total_trades = self.df["trade_id"].nunique()

        self._prepare_entry_exit_stats()
        self._prepare_tech_fetures()
        self._prepare_risk_features()
        

        #last
        self._prepare_buckets()
        self._prepare_day_stats()

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

    def gap_to_daily_pnl_stats(self, view: str = "tidy"):
        tidy = self.group_stats_df(
            df=self.daily,
            keys=["gap_bucket"],
            value_col="day_pnl",
            include_expectancy=False,
        )
        return tidy

    def entry_exit_stats_group(self, view: str = "tidy", grid_value: str = None):
        tidy = self.group_stats(keys=["time_bucket"], value_col="pnl", include_expectancy=False)
        if view == "multi":
            return self.as_multiindex(tidy, keys=["time_bucket"], cols=["count","mean","win_rate","tail_ratio_q05","expectancy","low_confidence"])
        if view == "grid" and grid_value:
            return self.grid(tidy, index="time_bucket", columns="adx_bucket", values=grid_value)
        return tidy

    def time_and_adx_stats(self, view: str = "tidy", grid_value: str = None):
        tidy = self.group_stats(keys=["time_bucket", "adx_bucket"], value_col="pnl",
            include_expectancy=False)
        if view == "multi":
            return self.as_multiindex(tidy, keys=["time_bucket", "adx_bucket"], cols=["count","mean","win_rate","tail_ratio_q05","expectancy","low_confidence"])
        if view == "grid" and grid_value:
            return self.grid(tidy, index="time_bucket", columns="adx_bucket", values=grid_value)
        return tidy

    def time_and_vwap_atr_stats(self, view: str = "tidy", grid_value: str = None):
        tidy = self.group_stats(keys=["time_bucket", "vwap_atr_bucket"], value_col="pnl",
            include_expectancy=False)
        if view == "multi":
            return self.as_multiindex(tidy, keys=["time_bucket", "vwap_atr_bucket"], cols=["count","mean","win_rate","tail_ratio_q05","expectancy","low_confidence"])
        if view == "grid" and grid_value:
            return self.grid(tidy, index="time_bucket", columns="vwap_atr_bucket", values=grid_value)
        return tidy
    
    def time_and_gap_pct_stats(self, view: str = "tidy", grid_value: str = None):
        gap_by_day = (
            df.groupby("trade_date", as_index=False)
            .agg(gap_bucket=("gap_bucket", "first"))
        )

        daily = daily.merge(gap_by_day, on="trade_date", how="left")

        tidy = self.group_stats(keys=["time_bucket", "gap_bucket"], value_col="pnl",
            include_expectancy=False)
        if view == "multi":
            return self.as_multiindex(tidy, keys=["time_bucket", "gap_bucket"], cols=["count","mean","win_rate","tail_ratio_q05","expectancy","low_confidence"])
        if view == "grid" and grid_value:
            return self.grid(tidy, index="time_bucket", columns="gap_bucket", values=grid_value)
        return tidy

    def time_and_bb_position_stats(self, view: str = "tidy", grid_value: str = None):
        tidy = self.group_stats(keys=["time_bucket", "bb_bucket"], value_col="pnl",
            include_expectancy=False)
        if view == "multi":
            return self.as_multiindex(tidy, keys=["time_bucket", "bb_bucket"], cols=["count","mean","win_rate","tail_ratio_q05","expectancy","low_confidence"])
        if view == "grid" and grid_value:
            return self.grid(tidy, index="time_bucket", columns="bb_bucket", values=grid_value)
        return tidy
    
    def time_and_vix1d_stats(self, view: str = "tidy", grid_value: str = None):
        tidy = self.group_stats(keys=["time_bucket", "vix1d_bucket"], value_col="pnl",
            include_expectancy=False)
        if view == "multi":
            return self.as_multiindex(tidy, keys=["time_bucket", "vix1d_bucket"], cols=["count","mean","win_rate","tail_ratio_q05","expectancy","low_confidence"])
        if view == "grid" and grid_value:
            return self.grid(tidy, index="time_bucket", columns="vix1d_bucket", values=grid_value)
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

    def group_stats_df(self, df: pd.DataFrame, keys: list[str], value_col: str = "pnl", **kwargs):
        orig = self.df
        try:
            self.df = df
            return self.group_stats(keys=keys, value_col=value_col, **kwargs)
        finally:
            self.df = orig
            
    def group_stats(self, keys: list[str], value_col: str = "pnl", q_low=(0.01, 0.05), q_high=(0.95,),
            include_expectancy: bool = True, min_count: int = 20, eps_mean: float = 1e-12, 
            add_tail_ratios: bool = True, add_upside_ratios: bool = False,
            win_threshold: float = 0.0, zero_is_loss: bool = True,
            extra_aggs: dict[str, dict[str, str]] | None = None
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
        if extra_aggs:
            gx = self.df.groupby(keys, dropna=False)
            for col, named_aggs in extra_aggs.items():
                tmp = gx[col].agg(**named_aggs).reset_index()
                out = out.merge(tmp, on=keys, how="left")
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

    @staticmethod
    def pivot_view(tidy: pd.DataFrame, index: str, columns: str, values: str):
        """
        Show me this metric laid out as rows × columns
        """
        return tidy.pivot_table(index=index, columns=columns, values=values, aggfunc="first")

    def as_multiindex(self, tidy: pd.DataFrame, keys: list[str], cols=None) -> pd.DataFrame:
        cols = cols or [c for c in tidy.columns if c not in keys]
        return tidy.set_index(keys).sort_index()[cols]

    def grid(self, tidy: pd.DataFrame, index: str, columns: str, values: str) -> pd.DataFrame:
        return tidy.pivot_table(index=index, columns=columns, values=values, aggfunc="first")


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

    def get_trade_entry_cadence(self):
        return df["mins_since_prev_trade"].describe(percentiles=[0.1, 0.25, 0.5, 0.75, 0.9])

    def get_trades_per_day(self):
        trades_per_day = self.df.groupby("trade_date").size()
        return trades_per_day

    def _prepare_entry_exit_stats(self):
        

        self.df["pos.entry"] = pd.to_datetime(self.df["pos.position.entry_time"], errors="coerce")
        self.df["pos.entry_tz"] = pd.to_datetime(self.df["pos.position.entry_time"], errors="coerce", utc=True).dt.tz_convert(None)

        self.df["mins_since_prev_trade"] = (
            self.df["pos.entry_tz"] - self.df["pos.entry_tz"].shift(1)
        ).dt.total_seconds() / 60

        self.df["pos.exit"] = pd.to_datetime(self.df["pos.position.exit_time"], errors="coerce")
        self.df["pos.exit_tz"] = pd.to_datetime(self.df["pos.position.exit_time"], errors="coerce", utc=True).dt.tz_convert(None)

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

        
    
    def _prepare_tech_fetures(self):
        price = self.df["pos.position.technicals.current_price"]
        vwap  = self.df["pos.position.technicals.current_vwap"]
        atr   = self.df["pos.position.technicals.current_atr"]
        
        bb_lo = self.df["pos.position.technicals.current_bb.lower"]
        bb_hi = self.df["pos.position.technicals.current_bb.upper"]

        open_ = self.df["pos.position.technicals.current_open"]
        prevc = self.df["pos.position.technicals.prev_day_close"]

        # (price - vwap) in ATR units
        self.df["price_vs_vwap_atr"] = (price - vwap) / atr.replace(0, np.nan)

        # Bollinger position 0..1 (can be <0 or >1 if outside the bands)
        denom = (bb_hi - bb_lo).replace(0, np.nan)
        self.df["bb_position"] = (price - bb_lo) / denom

        # Gap % vs prev close
        self.df["gap_pct"] = (open_ - prevc) / prevc.replace(0, np.nan)

        
        self.df["vix1d"] = self.df["pos.position.technicals.current_vix1d"]

    def _prepare_risk_features(self):

        # Max loss normalized by credit (loss per 1 credit)
        credit = self.df["ic.total_credit"]
        self.df["max_loss"] = self.df["ic.max_loss"].abs()
        self.df["max_loss_norm"] = self.df["max_loss"] / credit.replace(0, np.nan)

        # underlying_price_at_entry = self.df["pos.position.underlying_at_exit"]
        # lo = underlying_price_at_entry - em * self.cfg.em_buffer
        # hi = underlying_price_at_entry + em * self.cfg.em_buffer
        # em_width = hi - lo
        em = self.df["ic.em"]
        self.df["em"] = em.replace(0, np.nan)



        self.df["cushion"] = self.df["ic.cushion"]
        self.df["cushion_norm"] = self.df["cushion"] / self.df["em"].replace(0, np.nan)
        self.df["cushion_breached"] = self.df["cushion"] < 0
        self.df["cushion_tight"] = self.df["cushion_norm"] < 0.10  
        self.df["cushion_norm_width"] = (
            self.df["cushion"]
            / (2 * self.df["em"] * self.cfg.em_buffer)
        ).replace([np.inf, -np.inf], np.nan)

        # use underlying_at_exit
        # but check this underlying_at_entry

    def risk_feature_nulls(self):
        cols = ["max_loss_norm", "cushion_norm", "cushion_norm_width"]
        return self.df[cols].isna().mean().sort_values(ascending=False)

    def _prepare_buckets(self):
        self.add_bucket(source_col="entry_minutes_since_open", bins=self.cfg.time_bins, labels=self.cfg.time_bins_labels, name="time_bucket")
        self.add_bucket(source_col="price_vs_vwap_atr", bins=self.cfg.price_vs_vwap_atr_bins, name="vwap_atr_bucket")
        self.add_bucket(source_col="pos.position.technicals.current_adx", bins=self.cfg.adx_bins, name="adx_bucket")
        self.add_bucket(source_col="bb_position", bins=self.cfg.bb_position_bins, name="bb_bucket")
        self.add_bucket(source_col="gap_pct", bins=self.cfg.gcp_pct_bins, name="gap_bucket")
        self.add_bucket(source_col="pos.position.technicals.current_vix", bins=self.cfg.vix_bins, name="vix_bucket")
        self.add_bucket(source_col="pos.position.technicals.current_rsi", bins=self.cfg.rsi_bins, name="rsi_bucket")
    
        self.df["vix1d"] = self.df["pos.position.technicals.current_vix1d"]
        vix1d = self.df["vix1d"].dropna()
        if len(vix1d) >= 20:
            self.vix1d_p30 = vix1d.quantile(0.30)
            self.vix1d_p70 = vix1d.quantile(0.70)
        else:
            self.vix1d_p30 = np.nan
            self.vix1d_p70 = np.nan
        vix1d_bins = self.resolve_bins(
            series=vix1d,
            bins=self.cfg.vix1d_bins,
            percentiles=self.cfg.vix1d_percentiles
        )
        self.add_bucket(source_col="pos.position.technicals.current_vix1d", bins=vix1d_bins, name="vix1d_bucket")


        em_bins = self.resolve_bins(series=self.df["ic.em"], bins=self.cfg.em_bins, percentiles=self.cfg.em_percentiles)
        self.add_bucket(source_col="ic.em", bins=em_bins, name="em_bucket")
        self.add_bucket("max_loss_norm", self.cfg.max_loss_norm_bins, "max_loss_norm_bucket")
        self.add_bucket("cushion_norm", self.cfg.cushion_norm_bins, "cushion_norm_bucket")
        self.df["cushion_breach_bucket"] = np.where(self.df["cushion_breached"], "BREACH", "OK")
        self.add_bucket("cushion_norm_width", self.cfg.cushion_norm_width_bins, "cushion_norm_width_bucket")



    def resolve_bins(self, series: pd.Series, bins, percentiles):
        resolved = []
        for b in bins:
            if isinstance(b, str):
                resolved.append(series.quantile(percentiles[b]))
            else:
                resolved.append(b)
        return resolved

    def _prepare_day_stats(self):
        self.df = self.df.dropna(subset=["pos.entry"])
        self.df["trade_date"] = self.df["pos.entry"].dt.date


        daily_pnl = (
            self.df.groupby("trade_date", as_index=False)
                .agg(
                    day_pnl=("pnl", "sum"),
                    trades=("pnl", "size"),
                )
            )

        # 2) daily gap regime (one per day)
        daily_gap = (
            self.df.groupby("trade_date", as_index=False)
            .agg(
                gap_pct=("gap_pct", "first"),
                gap_bucket=("gap_bucket", "first"),
            )
        )

        # 3) merged daily table (this is what you should bucket+stats on)
        self.daily = daily_pnl.merge(daily_gap, on="trade_date", how="left")
