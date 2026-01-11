from AlgorithmImports import *
from models import IronCondorPosition, OptionChainFinderResult

class OptionChainAnalyzer:

    """Scans option chains and selects contracts"""
    def __init__(self, algo, config, logger):
        self.algo = algo
        self.config = config
        self.logger = logger
    
    def get_all_expiries(self, chain):
        if chain.contracts is None and chain.contracts.values():
            return []
        expiries = set()

        for c in chain.contracts.values():
            expiries.add(c.expiry)
        
        return expiries
    
    def find_fixed_delta(self, symbol, expiry, now_time, underlying_price, delta_target) -> OptionChainFinderResult:
        result = OptionChainFinderResult()

        try:
            chain = self.get_chain(symbol)
            if not chain or len(chain) == 0:
                return None

            expiry_contracts = [x for x in chain if x.expiry == expiry]

            calls = [c for c in expiry_contracts if c.right == OptionRight.CALL 
                and c.greeks is not None and c.greeks.delta is not None]
            puts = [c for c in expiry_contracts if c.right == OptionRight.PUT 
                and c.greeks is not None and c.greeks.delta is not None]
            
            short_call = min(calls, key=lambda c: abs(c.greeks.delta - delta_target))
            short_put = min(puts, key=lambda c: abs(c.greeks.delta - delta_target))
            
            iv = self.get_implied_volatility(chain, expiry, underlying_price)
            em = self.get_expected_move(expiry, now_time, underlying_price, iv)

            result.calls = [short_call]
            result.puts = [short_put]
            result.iv = iv
            result.em = em
        except Exception as e:
            result.had_error = True
            result.exception = e
        return result


    def find_candidates(self, symbol, expiry, now_time, underlying_price) -> OptionChainFinderResult:
        result = OptionChainFinderResult()

        try:
            chain = self.get_chain(symbol)
            if not chain or len(chain) == 0:
                return None

            expiry_contracts = [x for x in chain if x.expiry == expiry]

            calls = [c for c in expiry_contracts if c.right == OptionRight.CALL]
            puts = [c for c in expiry_contracts if c.right == OptionRight.PUT]

            iv = self.get_implied_volatility(chain, expiry, underlying_price)
            em = self.get_expected_move(expiry, now_time, underlying_price, iv)

            result.calls = calls
            result.puts = puts
            result.iv = iv
            result.em = em
        except Exception as e:
            result.had_error = True
            result.exception = e
        return result


    def get_dte(self, expiry, now_date):
        return (expiry.date() - now_date).days
    
    def long_legs_for_short_fixed_width(self, symbol, short_contract, 
        expiry,
        fixed_width: int,
        direction: str
    ):
        chain = self.get_chain(symbol)
        if not chain or len(chain) == 0:
            return None

        expiry_contracts = [x for x in chain if x.expiry == expiry]

        if direction == "call":
            target_long_strike = short_contract.strike + fixed_width
            calls = [c for c in expiry_contracts if c.right == OptionRight.CALL 
                and c.strike is not None and _tradeable(c)]
            if not calls: return None
            long_call = min(
                calls,
                key=lambda c: abs(c.strike - target_long_strike)
            )
            return [long_call]
        else:
            target_long_strike = short_contract.strike - fixed_width
            puts = [c for c in expiry_contracts if c.right == OptionRight.PUT 
                and c.strike is not None and _tradeable(c)]
            if not puts: return None
            long_put = min(
                puts,
                key=lambda c: abs(c.strike - target_long_strike)
            )
            return [long_put]

    def _tradeable(c) -> bool:
        """
        Why use a tradeable filter at all?
        Even in “no filters” baseline, this isn’t an alpha filter — it’s data hygiene. It prevents your long leg from landing on a dead strike with a crazy spread that corrupts PnL.
        The one change you should make
        Guard against missing quotes and use mid (or ask) for the denominator. Also, 0.5 (50%) is pretty lenient; for liquid underlyings you can often use 0.25–0.35. Keep it lenient for baseline.
        """
        mid = (c.bid + c.ask) / 2.0
        rel_spread = (c.ask - c.bid) / max(mid, 1e-6)
        return (c.bid is not None and c.ask is not None and c.bid > 0 and c.ask > c.bid 
            and rel_spread <= max_rel_spread)

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

        
    def get_chain(self, symbol):
        if self.algo.current_slice.option_chains.count == 0 or not self.algo.current_slice.option_chains[self.config.symbol]:
            return None
        else:
            return self.algo.current_slice.option_chains[symbol]
        
        
    def get_contract_from_chain(self, contract, symbol):
        if contract is None:
            return 
        chain = self.get_chain(symbol)
        if chain is None:
            return
        contract = next((c for c in chain if c.strike == contract.strike and c.right == contract.get_contract_type()), None)
        return contract

    def get_current_contract_legs_from_chain(self, symbol, contracts):
        current_contracts = []
        for c in contracts:
            current_contracts.append(self.get_contract_from_chain(c))

        return current_contracts


    def get_atm_contracts_and_iv(self, chain, expiry, underlying_price):
        # expiry = min([x.expiry for x in chain])
        expiry_contracts = [x for x in chain if x.expiry == expiry]

        # Sort by moneyness (distance from underlying price)
        sorted_contracts = sorted(expiry_contracts, key=lambda x: abs(underlying_price - x.strike))

        # Find the ATM call and put (they'll be near the top)
        atm_call = next((c for c in sorted_contracts if c.right == OptionRight.CALL), None)
        atm_put = next((c for c in sorted_contracts if c.right == OptionRight.PUT), None)

        if atm_call and atm_put:
            return {
                'atm_call': atm_call, 'atm_put': atm_put,
                'atm_call_iv': atm_call.implied_volatility, 'atm_put_iv': atm_put.implied_volatility
            }
        return None
    

    def get_implied_volatility(self, chain, expiry, underlying_price):
        atm_contracts = self.get_atm_contracts_and_iv(chain, expiry, underlying_price)
        avg_iv = (atm_contracts['atm_put_iv'] + atm_contracts['atm_call_iv']) / 2
        return avg_iv

    def get_expected_move(self, expiry, today_datetime, underlying_price, iv):
        SECONDS_PER_YEAR = 365.0 * 24.0 * 60.0 * 60.0
        TRADING_MINUTES_PER_YEAR = 252.0 * 6.5 * 60.0  # ≈ 98,280

        expiry_dt = expiry.replace(hour=16, minute=0, second=0, microsecond=0)
        seconds_to_expiry = (expiry_dt - today_datetime).total_seconds()
        seconds_to_expiry = max(seconds_to_expiry, 0)
        dte_days = seconds_to_expiry / 86400.0

        if dte_days < 7:
            # use minutes (better for short-dated / 0DTE)
            minutes_to_expiry = seconds_to_expiry / 60.0
            t_years = minutes_to_expiry / TRADING_MINUTES_PER_YEAR
        else:
            # use calendar time
            t_years = seconds_to_expiry / SECONDS_PER_YEAR
        em = underlying_price * iv * math.sqrt(t_years)

        return em

    
