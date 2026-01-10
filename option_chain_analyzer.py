from AlgorithmImports import *
from iron_condor_position import IronCondorPosition

class OptionChainAnalyzer:

    """Scans option chains and selects contracts"""
    def __init__(self, algo, config, logger):
        self.algo = algo
        self.config = config
        self.logger = logger
    
    def get_dte(self, expiry, now_date):
        return (expiry.date() - now_date).days
    
    def find_contract_candidates(self, chain, current_time, symbol, dte_range: tuple[int,int], put_delta_range: tuple[float,float], call_delta_range: tuple[float,float],
        spread_width_range: tuple[int,int]):
        
        chain = self.get_chain(symbol)
        if not chain or len(chain) == 0:
            return None

        min_dte, max_dte = dte_range
        today = current_time.date()

        min_expiry_date = today + timedelta(days=min_dte)
        max_expiry_date = today + timedelta(days=max_dte)

        expiry_contracts = [
            c for c in chain
            if min_dte <= self.get_dte(c.expiry, today) <= max_dte
        ]

        calls = [c for c in expiry_contracts if c.right == OptionRight.CALL]
        puts  = [p for p in expiry_contracts if p.right == OptionRight.PUT]

        call_low, call_high = call_delta_range          # e.g. (0.15, 0.20)
        put_low, put_high = put_delta_range           # e.g. (-0.20, -0.15)
        spread_min, spread_max = spread_width_range

        short_call_candidates = [c for c in calls
                        if c.greeks and c.greeks.delta is not None
                        and call_low <= c.greeks.delta <= call_high]

        short_put_candidates = [p for p in puts
                        if p.greeks and p.greeks.delta is not None
                        and put_low <= p.greeks.delta <= put_high]

        if not short_call_candidates or not short_call_candidates:
            return None

        call_spreads = {}
        for short_call in short_call_candidates:
            longs = self.long_legs_for_short(
                short_call, calls, spread_width_range, "call"
            )
            if longs:
                call_spreads[short_call] = longs

        put_spreads = {}
        for short_put in short_put_candidates:
            longs = self.long_legs_for_short(
                short_put, puts, spread_width_range, "put"
            )
            if longs:
                put_spreads[short_put] = longs
        return {
            "short_calls": short_call_candidates,
            "short_puts": short_put_candidates,
            "call_spreads": call_spreads,  # call_spreads: dict[Contract, list[Contract]]
            "put_spreads": put_spreads    # put_spreads:  dict[Contract, list[Contract]]
        }

    def long_legs_for_short(self, short_contract, same_side_contracts, 
        width_range: tuple[float, float],
        direction: str
    ):
        min_w, max_w = width_range

        if direction == "call":
            return [
                c for c in same_side_contracts
                if c.strike > short_contract.strike
                and min_w <= (c.strike - short_contract.strike) <= max_w
            ]
        else:
            return [
                p for p in same_side_contracts
                if p.strike < short_contract.strike
                and min_w <= (short_contract.strike - p.strike) <= max_w
            ]

    def find_position(self, symbol) -> IronCondorPosition:
        chain = self.get_chain(symbol)
        if not chain or len(chain) == 0:
            return None

        # expiry_contracts = [x for x in chain if x.expiry == expiry]

        calls = [c for c in chain if c.right == OptionRight.CALL]
        puts = [c for c in chain if c.right == OptionRight.PUT]

        # short_put = min(puts, key=lambda x: abs(x.greeks.delta - (-0.2)))
        # short_call = min(calls, key=lambda x: abs(x.greeks.delta - 0.2))
        short_call_delta_target = self.config.short_call_delta
        short_put_delta_target = self.config.short_put_delta
        short_call = max([x for x in calls if x.greeks.delta < short_call_delta_target], key=lambda x: x.greeks.delta)
        short_put = max([x for x in puts if x.greeks.delta < short_put_delta_target], key=lambda x: x.greeks.delta)

        
        short_put_strike = short_put.strike
        short_call_strike = short_call.strike
        
        long_leg_target_strike_distance = self.config.call_spread_width
        
        # Find long legs by strike distance (at least 2 away, prefer exactly 2)
        # Long put should have a lower strike than short put
        valid_long_puts = [p for p in puts if p.strike <= short_put.strike - long_leg_target_strike_distance]
        if valid_long_puts:
            long_put = min(valid_long_puts, key=lambda x: abs(x.strike - (short_put.strike - long_leg_target_strike_distance)))
        else:
            long_put = None

        # Long call should have a higher strike than short call
        valid_long_calls = [c for c in calls if c.strike >= short_call.strike + long_leg_target_strike_distance]
        if valid_long_calls:
            long_call = min(valid_long_calls, key=lambda x: abs(x.strike - (short_call.strike + long_leg_target_strike_distance)))
        else:
            long_call = None
        # def __init__(self, symbol, long_put: OptionContract, short_put: OptionContract, short_call: OptionContract, long_call: OptionContract):
        if long_put and long_call:
            position = IronCondorPosition(symbol, long_put, short_put, short_call, long_call)
            return position
        else:
            return None
        
    def get_chain(self, symbol):
        if self.algo.current_slice.option_chains.count == 0 or not self.algo.current_slice.option_chains[self.config.symbol]:
            return None
        else:
            return self.algo.current_slice.option_chains[symbol]
        
        
    def get_contract_from_chain(self, contract):
        chain = self.get_chain(contract.symbol)
        contract = next((c for c in chain if c.strike == contract.strike and c.right == contract.get_contract_type()), None)
        return contract

    def get_current_contract_legs_from_chain(self, contracts):
        current_contracts = []
        for c in contracts:
            current_contracts.append(self.get_contract_from_chain(c))

        return current_contracts


    def get_atm_contracts_and_iv(self, chain, expiry):
        # expiry = min([x.expiry for x in chain])
        expiry_contracts = [x for x in chain if x.expiry == expiry]

        # Sort by moneyness (distance from underlying price)
        sorted_contracts = sorted(expiry_contracts, key=lambda x: abs(x.underlying.price - x.strike))

        # Find the ATM call and put (they'll be near the top)
        atm_call = next((c for c in sorted_contracts if c.right == OptionRight.CALL), None)
        atm_put = next((c for c in sorted_contracts if c.right == OptionRight.PUT), None)

        if atm_call and atm_put:
            return {
                'atm_call': atm_call, 'atm_put': atm_put,
                'atm_call_iv': atm_call.IV, 'atm_put_iv': atm_put.IV
            }
        return None
    
    def get_chain_expected_move(self, chain, expiry, today_datetime, underlying_price):
        # make sure pulling correct value for ImpliedVolatility
        atm_contracts = self.get_atm_contracts_and_iv(chain, expiry)
        avg_iv = (atm_contracts['atm_put_iv'] + atm_contracts['atm_call_iv']) / 2
        dte = (expiry - today_datetime).total_seconds() / 86400.0
        dte = max(dte, 0.0)
        # Expected Move ≈ Price × IV × √(DTE / 365)
        import math
        em = underlying_price * avg_iv * math.sqrt(dte / 365)
        return em

    
