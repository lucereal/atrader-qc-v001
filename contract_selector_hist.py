# region imports
from AlgorithmImports import *
from config import ContractSelectionConfig
# endregion

# in future make this an interface
# then have several "contractSelectoryStrategies" like "(DeltaStrategy, IVWeightedStrategy, ProbabilityStrategy)"
# to test other strats with same algo

class ContractSelector:
    def __init__(self, config, logger, chain_analyzer):
        self.config = config
        self.logger = logger
        self.chain_analyzer = chain_analyzer

    def select_iron_condor_legs(self, chain, current_time, symbol, underlying_price, sel_cfg: ContractSelectionConfig):
        """
        Main entry point. Returns dict with selected strikes:
        {'short_put': strike, 'long_put': strike, 'short_call': strike, 'long_call': strike}
        """
        contract_candidates = self.chain_analyzer.find_contract_candidates(chain, current_time, symbol, 
            sel_cfg.dte_range, sel_cfg.short_put_delta_range, sel_cfg.short_call_delta_range,
            sel_cfg.spread_width_range)

        return contract_candidates
  
    def _score_call_spread(self, short, long):
        pass

    

    # What you’re computing is the standard “expected move” (one standard deviation). Great. Later you’ll apply a multiplier (1.0–1.2x).
    



# OPTION SELECTION CHECKLIST
# (applies only if the day passes the No-Trade filters)
# 	Credit vs Risk (most important)
# 		Credit is at least 25–35% of the spread width
# 		Maximum loss per iron condor is below a predefined percentage of portfolio equity
# 		Skip the trade if premium is thin even when deltas look acceptable
# 	Short Leg Delta Range
# 		Short call delta between +0.15 and +0.25
# 		Short put delta between −0.15 and −0.25
# 		Prefer symmetry so both short strikes are a similar percentage distance from spot
        # Both short strikes represent similar probability distance from spot
        # sym doesn't mean same absolute deltas or same exact distance away for strikes
#       option A: abs(call_delta) ≈ abs(put_delta) which is delta symmetry
        # - this aligns probability of touch, tail risk balance, gamma exposure
#       option B: Distance-from-spot symmetry
#       option A is prefered
#       avoid 
#           focing exact sym
#           Picking highest credit only
#           Ignoring wing structure - one wing tight, one wide
#           That’s why credit ratio and width checks come after selection. 
#       order:
        # Delta range filter (this rule)
        # Symmetry preference
        # Credit ratio / risk gates
        # Sizing
# 	Avoid Major Price Levels
# 		Short strikes are not near prior day high or prior day low
# 		Short strikes are not near VWAP
# 		Short strikes are not near large open-interest or obvious congestion levels
# 	Wing Width (Gamma Control)
# 		Wing width is wide enough to absorb normal intraday noise
# 		Wing width scales up on higher implied volatility days
# 		Avoid very narrow spreads chosen only because they are cheap

#  next most important for remaining conditions
# 	Distance vs Expected Move
# 		Short strikes are outside 1.0–1.2 times the expected move
# 		Skip the trade if the expected move overlaps either short strike
#       Distance vs Expected Move (MOST important of the remaining)
        # Expected Move (EM) is the market’s own forecast of range
        # If your short strike is inside EM, you are:
        # selling premium against expected movement
        # structurally mispriced for a short-gamma trade
        # This filter catches:
        # event risk you missed
        # high IV days where deltas lie
        # days where price action looks calm until it isn’t
        # Short strikes should be outside 1.0–1.2 × expected move
        # If EM overlaps either short strike → skip
        # This filter is orthogonal to delta, VWAP, ADX — it protects a different failure mode.
    # expected move - 1 standard deviation price move implied by options over a given time period
    # Expected Move ≈ Price × IV × √(DTE / 365)
    # Option 1 (BEST / RECOMMENDED): Compute EM from ATM IV in the option chain
    # Conceptual steps (no editor code):
        # From the option chain for your target expiry:
        # Find ATM call + ATM put
        # Or the contract with delta closest to ±0.50
        # Extract Implied Volatility
        # Use mid IV (or average call/put IV)
    # Compute EM:
        # Multiply IV by price
        # Scale by √(DTE / 365)
        # This gives you:
        # A market-implied expected range
        # Directly comparable to strike distance
        # Automatically adapts to IV regime
    # for our strikes
        # You want:
        # Short call strike > spot + EM × multiplier
        # Short put strike < spot − EM × multiplier
        # Where multiplier is:
            # 1.0 → aggressive
            # 1.1–1.2 → balanced (recommended)
            # > 1.3 → very conservative

# 	Expiration Choice
# 		Prefer 1–3 DTE on uncertain or mixed conditions
# 		Use 0DTE only on clearly range-bound days
# 	Avoid opening new iron condors late in the trading session
# 2nd next most important - Wing Width (Gamma Control)
    # This is next because it determines how violently you lose when you’re wrong.
    # Why it matters
    # Narrow wings = extreme gamma
    # Gamma is what kills ICs intraday, not theta
    # Many strategies quietly fail because wings are too tight
    # This is especially important for:
    # 0DTE
    # high IV days
    # fast markets
    # Good logic
    # Wing width should scale with:
    # ATR
    # IV
    # DTE
    # Avoid “cheap but tight” spreads
    # This doesn’t decide whether to trade — it decides survivability.

  
    def _find_short_put_strike(self, chain_analyzer, target_delta):
        """Find put strike closest to target delta (e.g., -0.20)"""
        pass
    
    def _find_short_call_strike(self, chain_analyzer, target_delta):
        """Find call strike closest to target delta (e.g., 0.20)"""
        pass
    
    def _find_long_put_strike(self, short_put_strike, current_price):
        """Find protective long put below the short put (width-based)"""
        pass
    
    def _find_long_call_strike(self, short_call_strike, current_price):
        """Find protective long call above the short call (width-based)"""
        pass
    
    def _validate_structure(self, short_put, long_put, short_call, long_call):
        """Verify strikes form valid iron condor: long_put < short_put < short_call < long_call"""
        pass
    
    def _score_legs(self, short_put, short_call):
        """Optional: rank legs by IV, prob of profit, credit collected, etc."""
        pass
