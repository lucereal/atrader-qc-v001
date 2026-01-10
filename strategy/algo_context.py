# region imports
from AlgorithmImports import *
# endregion


# pass this into classes instead of actual QCAlgorithm
class AlgoContext:
    def __init__(self, algo):
        self.algo = algo

    # market data access you actually use
    def time(self):
        return self.algo.Time

    def log(self, msg: str):
        self.algo.Debug(msg)

    def place_order(self, *args, **kwargs):
        return self.algo.MarketOrder(*args, **kwargs)

    def get_chain(self, option_symbol):
        return self.algo.CurrentSlice.OptionChains.get(option_symbol)
