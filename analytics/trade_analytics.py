# region imports
from AlgorithmImports import *
from models.candidates import IronCondorCandidate, VerticalCandidate
from models.iron_condor_position import IronCondorPosition, IronCondorLegs
# endregion

# Your New Python File

class TradeAnalytics:
    def __init__(self, logger):
        self.logger = logger
    
    def aggregate_trades(self, trades):
        num_trades = len(trades)
        position_rows = []
        for k, position in trades.items():   
            pos_stats = self.get_close_position_stats(position)
            ic = self.get_iron_condor_candidate_technicals(position.ic_candidate)
            position_rows.append({"pos": pos_stats, "ic": ic})
        
        return position_rows

    def get_iron_condor_candidate_technicals(self, ic: IronCondorCandidate):
        return ic.to_dict()
        

    def get_close_position_stats(self, position):
        pnl = position.get_exit_pnl()
        pnl_pct = position.get_exit_pnl_pct()
        position_stats = {
            'pnl': pnl, 
            'pnl_pct': pnl_pct,
            'entry': position.opening_legs.get_total_fill_price(),
            'exit': position.closing_legs.get_total_fill_price(),
            'underlying_price_change': 0,
            'position': position.to_dict()
            
        }
        if position.underlying_at_buy >= position.underlying_at_sell:
            position_stats['underlying_price_change'] = position.underlying_at_sell - position.underlying_at_buy
        else:
            position_stats['underlying_price_change'] = position.underlying_at_buy - position.underlying_at_sell
        return position_stats

            
