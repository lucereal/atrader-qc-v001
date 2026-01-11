# region imports
from AlgorithmImports import *
from models import VerticalCandidate, IronCondorCandidate
# endregion
class OptionMetrics:


    # WORKFLOW
        # build vertical candidates
        # (optional) spread level filtering - filter verticals by credit/ratio/liquidity - keep top N per side
        # build IC candidates
            # when pairing put and call verticals
            # apply _is_risk_defined as hard gate
            # build IronCondorCandidate (credit, rr, cushion, em_ok)
            # compute centering_score + delta_balance_score on the fly
            # use those in your composite score (or as soft filters)
    @staticmethod
    def vertical_candidate(short, long, side: str) -> VerticalCandidate:
        """
        Conservative credit: short.bid - long.ask
        Width: abs(long.strike - short.strike)
        """
        pricing = "mid"
        width = OptionMetrics._width(short, long)

        if pricing == "mid":
            credit = OptionMetrics._mid_credit(short, long)
        else:
            credit = OptionMetrics._conservative_credit(short, long)

        conservative_credit = OptionMetrics._conservative_credit(short, long)

        credit_ratio = OptionMetrics._credit_ratio(credit, width)
        short_delta, long_delta = OptionMetrics._deltas(short, long)

        return VerticalCandidate(
            side=side,
            short=short,
            long=long,
            width=width,
            credit=credit,
            credit_ratio=credit_ratio,
            short_delta=float(short_delta) if short_delta is not None else None,
            long_delta=float(long_delta) if long_delta is not None else None,
        )

    @staticmethod
    def iron_condor_candidate(
        put_v: VerticalCandidate,
        call_v: VerticalCandidate,
        underlying_price: float,
        expected_move: float,
        em_buffer: float = 1.0,
    ) -> IronCondorCandidate:
        total_credit = OptionMetrics._ic_total_credit(put_v, call_v)
        max_width = OptionMetrics._ic_max_width(put_v, call_v)
        max_loss = OptionMetrics._ic_max_loss(total_credit, max_width)
        rr = OptionMetrics._reward_risk(total_credit, max_loss)

        lo, hi = OptionMetrics._em_bounds(underlying_price, expected_move, em_buffer)
        sp_strike, sc_strike = OptionMetrics._short_strikes(put_v, call_v)

        em_ok = OptionMetrics._em_ok(sp_strike, sc_strike, lo, hi)
        cushion = OptionMetrics._cushion(sp_strike, sc_strike, lo, hi)

        return IronCondorCandidate(
            put=put_v,
            call=call_v,
            total_credit=total_credit,
            max_loss=max_loss,
            rr=rr,
            em_ok=em_ok,
            cushion=cushion,
            em=expected_move
        )



# center = OptionMetrics._ic_centering_score(pv, cv, underlying_price)
# balance = OptionMetrics._ic_delta_balance_score(pv, cv)

# # Example combined score (tune weights)
# score = (
#     2.0 * ic.rr +
#     1.0 * ic.cushion +
#     0.5 * center +
#     0.5 * balance
# )


# _ic_delta_balance_score
    # For a delta-neutral-ish IC, the short deltas should “cancel”:
    #     short call delta is positive
    #     short put delta is negative
    # Compute:
    #     net_delta = short_call_delta + short_put_delta
    #     ideal net_delta ≈ 0
    #     Turn that into a score in [0, 1]:
   

# _ic_centering_score
    # Goal: prefer ICs where the short strikes are roughly symmetric around spot.
    #     A simple, stable score is based on distances from spot:
    #     d_put = spot - short_put_strike (positive if short_put below spot)
    #     d_call = short_call_strike - spot (positive if short_call above spot)
    #     perfect symmetry when d_put == d_call
    # Score in [0, 1]:
    #     1 = perfectly centered
    #     0 = very lopsided or invalid
    # If you want it to penalize “too tight” as well, you can multiply by a “distance” factor, but the symmetry ratio alone is a great first signal.



# _is_defined_risk
    # GOAL
        # validates strikes are ordered correctly
    # USAGE 
        # use it as a hard gate before scoring:
        # if not OptionMetrics._is_defined_risk(pv, cv, underlying_price, require_brackets_spot=True): continue
    # CHECKS
        # each vertical’s strikes are ordered correctly for a credit spread
        # the condor is “properly shaped” (no inverted wings)
        # (optional) short strikes bracket spot


    @staticmethod
    def _is_credit_vertical(v: VerticalCandidate) -> bool:
        """
        Validate strike ordering for a CREDIT vertical:
          put credit spread:  short strike > long strike
          call credit spread: short strike < long strike
        """
        s = OptionMetrics._strike(v.short)
        l = OptionMetrics._strike(v.long)

        if v.side == "put":
            return s > l
        if v.side == "call":
            return s < l
        return False

    @staticmethod
    def _is_defined_risk(
        put_v: VerticalCandidate,
        call_v: VerticalCandidate,
        underlying_price: float | None = None,
        require_brackets_spot: bool = False,
    ) -> bool:
        """
        IC should look like:
          long_put < short_put < short_call < long_call

        plus each vertical must be credit-shaped.
        """
        if put_v.side != "put" or call_v.side != "call":
            return False

        if not OptionMetrics._is_credit_vertical(put_v):
            return False
        if not OptionMetrics._is_credit_vertical(call_v):
            return False

        lp = OptionMetrics._strike(put_v.long)
        sp = OptionMetrics._strike(put_v.short)
        sc = OptionMetrics._strike(call_v.short)
        lc = OptionMetrics._strike(call_v.long)

        # Proper condor ordering
        if not (lp < sp < sc < lc):
            return False

        if require_brackets_spot and underlying_price is not None:
            if not (sp < underlying_price < sc):
                return False

        return True

    @staticmethod
    def _ic_centering_score(
        put_v: VerticalCandidate,
        call_v: VerticalCandidate,
        underlying_price: float,
        eps: float = 1e-9,
    ) -> float:
        """
        Symmetry score in [0,1].
        1.0 means short strikes are equally far from spot.
        0.0 means very lopsided or doesn't bracket spot.
        """
        sp = OptionMetrics._strike(put_v.short)
        sc = OptionMetrics._strike(call_v.short)

        d_put = underlying_price - sp
        d_call = sc - underlying_price

        # must bracket spot to make sense
        if d_put <= 0 or d_call <= 0:
            return 0.0

        return float(min(d_put, d_call) / (max(d_put, d_call) + eps))

    @staticmethod
    def _ic_delta_balance_score(
        put_v: VerticalCandidate,
        call_v: VerticalCandidate,
        eps: float = 1e-9,
        missing_score: float = 0.0,
    ) -> float:
        """
        Uses short deltas to measure balance.
        Returns [0,1], where 1 = best balanced (net delta near 0).
        """
        spd = put_v.short_delta
        scd = call_v.short_delta

        if spd is None or scd is None:
            return float(missing_score)

        net = scd + spd  # call is +, put is -
        total_mag = abs(scd) + abs(spd)

        imbalance = abs(net) / (total_mag + eps)  # 0 best, 1 worst-ish
        score = 1.0 - imbalance

        # clamp
        if score < 0.0:
            score = 0.0
        elif score > 1.0:
            score = 1.0

        return float(score)



# helper methods
# 

    @staticmethod
    def _get_bid_ask(c) -> tuple[float, float]:
        """
        Returns (bid, ask). Falls back to 0.0 if missing.
        Adjust field names if your contract uses different properties.
        """
        bid = getattr(c, "bid", None)
        ask = getattr(c, "ask", None)

        if bid is None: bid = getattr(c, "BidPrice", None)
        if ask is None: ask = getattr(c, "AskPrice", None)

        # Some QC objects use Bid/Ask
        if bid is None: bid = getattr(c, "Bid", None)
        if ask is None: ask = getattr(c, "Ask", None)

        bid = float(bid) if bid is not None else 0.0
        ask = float(ask) if ask is not None else 0.0
        return bid, ask

    @staticmethod
    def _is_credit_vertical(v: VerticalCandidate) -> bool:
        s = OptionMetrics._strike(v.short)
        l = OptionMetrics._strike(v.long)

        if v.side == "put":
            # credit put spread: short put strike ABOVE long put strike
            return s > l
        elif v.side == "call":
            # credit call spread: short call strike BELOW long call strike
            return s < l
        return False

    @staticmethod
    def _strike(c) -> float:
        return float(getattr(c, "strike"))

    @staticmethod
    def _ic_total_credit(put_v: VerticalCandidate, call_v: VerticalCandidate) -> float:
        return put_v.credit + call_v.credit

    @staticmethod
    def _ic_max_width(put_v: VerticalCandidate, call_v: VerticalCandidate) -> float:
        return max(put_v.width, call_v.width)

    @staticmethod
    def _ic_max_loss(total_credit: float, max_width: float) -> float:
        # Defined-risk IC uses max(widths) - total_credit
        return max_width - total_credit

    @staticmethod
    def _reward_risk(total_credit: float, max_loss: float) -> float:
        return (total_credit / max_loss) if max_loss > 0 else 0.0

    @staticmethod
    def _em_bounds(underlying_price: float, expected_move: float, em_buffer: float) -> tuple[float, float]:
        lo = underlying_price - expected_move * em_buffer
        hi = underlying_price + expected_move * em_buffer
        return lo, hi

    @staticmethod
    def _short_strikes(put_v: VerticalCandidate, call_v: VerticalCandidate) -> tuple[float, float]:
        sp = float(getattr(put_v.short, "strike"))
        sc = float(getattr(call_v.short, "strike"))
        return sp, sc

    @staticmethod
    def _em_ok(short_put_strike: float, short_call_strike: float, lo: float, hi: float) -> bool:
        return (short_put_strike <= lo) and (short_call_strike >= hi)

    @staticmethod
    def _cushion(short_put_strike: float, short_call_strike: float, lo: float, hi: float) -> float:
        """
        Positive cushion means extra room beyond EM bounds.
        Negative cushion means EM breaches a short strike.
        """
        return min(lo - short_put_strike, short_call_strike - hi)

    @staticmethod
    def _width(short, long) -> float:
        return abs(float(long.strike) - float(short.strike))

    @staticmethod
    def _conservative_credit(short, long) -> float:
        short_bid, _ = OptionMetrics._get_bid_ask(short)
        _, long_ask = OptionMetrics._get_bid_ask(long)
        return max(0.0, short_bid - long_ask)

    @staticmethod
    def _mid_credit(short, long) -> float:
        sb, sa = OptionMetrics._get_bid_ask(short)
        lb, la = OptionMetrics._get_bid_ask(long)
        short_mid = (sb + sa) / 2 if (sb > 0 and sa > 0) else 0.0
        long_mid  = (lb + la) / 2 if (lb > 0 and la > 0) else 0.0
        return max(0.0, short_mid - long_mid)

    @staticmethod
    def _credit_ratio(credit: float, width: float) -> float:
        return (credit / width) if width > 0 else 0.0

    @staticmethod
    def _deltas(short, long):
        sd = getattr(getattr(short, "greeks", None), "delta", None)
        ld = getattr(getattr(long, "greeks", None), "delta", None)
        return (float(sd) if sd is not None else None,
                float(ld) if ld is not None else None)
