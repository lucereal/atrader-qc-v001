# region imports
from AlgorithmImports import *
from models.iron_condor_position import IronCondorPosition, PositionStatus
import json 
from models.trade_group import TradeGroup
# endregion

# keep position state in here.
# Position tracking and awareness (knowning which positions exist)
# Position level risk checks (can we manage, add to this position)
# Position sizing calculations
# Portfolio level constraints (max positions, risk limits, etc)


class PortfolioManager:
    def __init__(self, algo, config, logger):
        self.algo = algo
        self.logger = logger
        self.config = config
        self.current_position = None
        self.trade_entered_today = False
        self.last_date = None
        self.open_positions_by_symbol = {}
        self.all_positions = {}
        self.open_positions = {}
        self.closed_positions = {}
        self.canceled_positions = {}
        self.date_to_position = {}
        self.trades_today = []
        

    def get_current_positions(self):
        return self.open_positions

    def can_manage_position(self, position):
        return True
    
        
    def on_position_opened(self, trade_group: TradeGroup):
        position = self.all_positions[trade_group.trade_group_id]
        position.set_position_status(PositionStatus.OPENED)
        
        for order in trade_group.opening_orders:
            position.opening_legs.set_fill_price(order.symbol, order.fill_price)
        
        total_fill_price = position.opening_legs.get_total_fill_price()
        
        self.trades_today.append(position)
        self.open_positions[trade_group.trade_group_id] = self.all_positions[trade_group.trade_group_id]
        self.date_to_position[self.algo.time.date().strftime("%Y-%m-%d")] = trade_group.trade_group_id

        return
    
    def on_position_closed(self, trade_group: TradeGroup):
        position = self.open_positions[trade_group.trade_group_id]
        position.set_position_status(PositionStatus.CLOSED)

        for order in trade_group.closing_orders:
            position.closing_legs.set_fill_price(order.symbol, order.fill_price)

        total_fill_price = position.closing_legs.get_total_fill_price()
        total_opening_price = position.opening_legs.get_total_fill_price()

        total_pnl = position.get_exit_pnl()

        self.closed_positions[trade_group.trade_group_id] = position
        del self.open_positions[trade_group.trade_group_id]
        return
    
    def on_order_cancelled(self, trade_group, order_type):
        position = self.all_positions[trade_group.trade_group_id]
        position.set_position_status(PositionStatus.CANCELED)
        self.canceled_positions[trade_group.trade_group_id] = position
        return    
        

    def on_order_submitted(self, position: IronCondorPosition, trade_group):
        position.set_position_status(PositionStatus.SUBMITTED)
        self.all_positions[trade_group.trade_group_id] = position
        self.trade_entered_today = True
        return

    # def get_holdings_stats(self):
    #     security_holding = self.portfolio["SPY"]
    #     quantity = security_holding.quantity
    #     invested = security_holding.invested
    #     profit = self.portfolio["SPY"].total_close_profit()

    # def set_initial_holdings(self):
    #     if not self.live_mode:
    #         self.set_cash(100000)       # Set the quantity of the account currency to 100,000
    #         self.set_cash("BTC", 10)    # Set the Bitcoin quantity to 10
    #         self.set_cash("EUR", 10000) # Set the EUR quantity to 10,000

    # def on_end_of_day(self, symbol: Symbol) -> None:
    #     # Obtain the algorithm statistics interested.
    #     sharpe = self.statistics.total_performance.portfolio_statistics.sharpe_ratio
    #     b = self.statistics.total_performance.portfolio_statistics.beta
    #     var = self.statistics.total_performance.portfolio_statistics.value_at_risk_95

    #     # Plot the statistics.
    #     self.plot("Statistics", "Sharpe", sharpe)
    #     self.plot("Statistics", "Beta", b)
    #     self.plot("Statistics", "Value-at-Risk", var)

    #     # Write to save the statistics.
    #     self._statistics.append(f'{self.time.strftime("%Y%m%d")},{sharpe},{b},{var}')

    # def on_end_of_algorithm(self) -> None:
    #     # Save the logged statistics for later access in the object store.
    #     self.object_store.save(f'{self.project_id}/algorithm-statistics', '\n'.join(self._statistics))

    # def set_trade_builder(self):
    #     self.set_trade_builder(TradeBuilder(FillGroupingMethod.FLAT_TO_FLAT, FillMatchingMethod.FIFO))
    #     trades = self.trade_builder.closed_trades

    #     if len(trades) > 4:
    #         # Use the trade builder to obtain the win rate and % return of the last five trades to calculate position size.
    #         last_five_trades = sorted(trades, key=lambda x: x.exit_time)[-5:]
    #         prob_win = len([x for x in last_five_trades if x.is_win]) / 5
    #         win_size = np.mean([x.profit_loss / x.entry_price for x in last_five_trades])
    #         # Use the Kelly Criterion to calculate the order size.
    #         size = max(0, prob_win - (1 - prob_win) / win_size)

    def calculate_stats(self):
        canceled_count = len(self.canceled_positions.keys())

        profit_target_reached = []
        loss_target_reached = []
        close_hour_target_reached = []
        
        close_stats_by_hour = self.get_close_stats_by_hour(self.closed_positions)
        close_stats_by_day = self.get_stats_by_day(self.closed_positions)
        all_closing_stats = self.get_all_closing_stats(self.closed_positions)

        for k, pos in self.closed_positions.items():
            if pos.exit_reason == "PROFIT_TARGET":
                profit_target_reached.append(pos)
            elif pos.exit_reason == "LOSS_TARGET":
                loss_target_reached.append(pos)
            elif pos.exit_reason == "CLOSE_HOUR_TARGET":
                close_hour_target_reached.append(pos)
                
        stats = {
            'all_pos_count': len(self.all_positions.keys()),
            'close_pos_count': len(self.closed_positions.keys()),
            'canceled_count': canceled_count,
            'profit_target_count': len(profit_target_reached),
            'loss_target_count': len(loss_target_reached),
            'close_hour_target_count': len(close_hour_target_reached),
            'all_closing_stats': all_closing_stats,
            'close_by_hour': close_stats_by_hour,
            'close_stats_by_day': close_stats_by_day
        }
        high_mid_low_pnl = self.get_high_mid_low_pnl(stats['all_closing_stats']['pnl_list'])

        return stats


    def get_all_closing_stats(self, closed_positions):
        stats = {
                'count': 0,
                'total_pnl': 0.0,
                'total_pnl_pct': 0.0,
                'avg_pnl': 0.0,
                'avg_pnl_pct': 0.0,
                'pnl_list': [],
                'wins': [],
                'losses': [],
                'avg_lose_pct': 0.0,
                'avg_win_pct': 0.0,
                'num_losses': 0,
                'num_wins': 0
            }
        
        for k, position in closed_positions.items():    
            
            position_stats = self.get_close_position_stats(position)
            stats['pnl_list'].append(position_stats)
            stats['count'] += 1
            stats['total_pnl'] += position_stats["pnl"]
            stats['total_pnl_pct'] += position_stats["pnl_pct"]

            if position_stats["pnl_pct"] > 0:
                stats['wins'].append(position_stats)
            else:
                stats['losses'].append(position_stats)

            num_wins = len(stats['wins'])
            num_losses = len(stats['losses'])
            stats['num_wins'] = num_wins
            stats['num_losses'] = num_losses
            total_wins_pnl_pct = sum(x['pnl_pct'] for x in stats['wins'])
            total_losses_pnl_pct = sum(x['pnl_pct'] for x in stats['losses'])
            stats['avg_pnl'] = stats['total_pnl'] / stats['count']
            stats['avg_pnl_pct'] = stats['total_pnl_pct'] / stats['count']

            if  num_wins > 0:
                stats['avg_win_pct'] = (total_wins_pnl_pct / num_wins)
                wins_avg_underlying_price_change = sum(x['underlying_price_change'] for x in stats['wins']) / num_wins
                stats['wins_avg_underlying_price_change'] = wins_avg_underlying_price_change
            if num_losses > 0:
                stats['avg_lose_pct'] = (total_losses_pnl_pct / num_losses)
                losses_avg_underlying_price_change = (sum(x['underlying_price_change'] for x in stats['losses']) / num_losses)
                stats['losses_avg_underlying_price_change'] = losses_avg_underlying_price_change
            
        return stats

    def get_stats_by_day(self, closed_positions):
        stats_by_day = {}
        for k, position in closed_positions.items():
            if position.exit_time:
                exit_date = position.exit_time.strftime("%Y-%m-%d")
                
                if exit_date not in stats_by_day:
                    stats_by_day[exit_date] = {
                        'count': 0,
                        'total_pnl': 0.0,
                        'total_pnl_pct': 0.0,
                        'avg_pnl': 0.0,
                        'avg_pnl_pct': 0.0,
                        'pnl_list': [],
                        'wins': [],
                        'losses': [],
                        'avg_lose_pct': 0.0,
                        'avg_win_pct': 0.0,
                        'num_losses': 0,
                        'num_wins': 0
                    }
                position_stats = self.get_close_position_stats(position)

                exit_period_stats = stats_by_day[exit_date]

                exit_period_stats['pnl_list'].append(position_stats)
                exit_period_stats['count'] += 1
                exit_period_stats['total_pnl'] += position_stats["pnl"]
                exit_period_stats['total_pnl_pct'] += position_stats["pnl_pct"]

                if position_stats["pnl_pct"] > 0:
                    exit_period_stats['wins'].append(position_stats)
                else:
                    exit_period_stats['losses'].append(position_stats)
            # Calculate averages
            for period in stats_by_day:
                period_stats = stats_by_day[period]
                avg_strike_delta = 0
                if period_stats['count'] > 0:
                    num_wins = len(period_stats['wins'])
                    num_losses = len(period_stats['losses'])
                    period_stats['num_wins'] = num_wins
                    period_stats['num_losses'] = num_losses
                    total_wins_pnl_pct = sum(x['pnl_pct'] for x in period_stats['wins'])
                    total_losses_pnl_pct = sum(x['pnl_pct'] for x in period_stats['losses'])
                    period_stats['avg_pnl'] = period_stats['total_pnl'] / period_stats['count']
                    period_stats['avg_pnl_pct'] = period_stats['total_pnl_pct'] / period_stats['count']

                    if  num_wins > 0:
                        period_stats['avg_win_pct'] = (total_wins_pnl_pct / num_wins)
                        wins_avg_underlying_price_change = sum(x['underlying_price_change'] for x in period_stats['wins']) / num_wins
                        period_stats['wins_avg_underlying_price_change'] = wins_avg_underlying_price_change
                    if num_losses > 0:
                        period_stats['avg_lose_pct'] = (total_losses_pnl_pct / num_losses)
                        losses_avg_underlying_price_change = (sum(x['underlying_price_change'] for x in period_stats['losses']) / num_losses)
                        period_stats['losses_avg_underlying_price_change'] = losses_avg_underlying_price_change
        return stats_by_day

    def get_close_stats_by_hour(self, closed_positions):
        stats_by_hour = {}
        
        for k, position in closed_positions.items():
            if position.exit_time:
                hour = position.exit_time.hour
                
                if hour not in stats_by_hour:
                    stats_by_hour[hour] = {
                        'count': 0,
                        'total_pnl': 0.0,
                        'total_pnl_pct': 0.0,
                        'avg_pnl': 0.0,
                        'avg_pnl_pct': 0.0,
                        'pnl_list': [],
                        'wins': [],
                        'losses': [],
                        'avg_lose_pct': 0.0,
                        'avg_win_pct': 0.0
                    }
                
                position_stats = self.get_close_position_stats(position)

                stats_by_hour[hour]['pnl_list'].append(position_stats)
                stats_by_hour[hour]['count'] += 1
                stats_by_hour[hour]['total_pnl'] += position_stats["pnl"]
                stats_by_hour[hour]['total_pnl_pct'] += position_stats["pnl_pct"]

                if position_stats["pnl_pct"] > 0:
                    stats_by_hour[hour]['wins'].append(position_stats)
                else:
                    stats_by_hour[hour]['losses'].append(position_stats)
        
        # Calculate averages
        for hour in stats_by_hour:
            avg_strike_delta = 0
            if stats_by_hour[hour]['count'] > 0:
                total_wins_pnl_pct = sum(x['pnl_pct'] for x in stats_by_hour[hour]['wins'])
                total_losses_pnl_pct = sum(x['pnl_pct'] for x in stats_by_hour[hour]['losses'])
                stats_by_hour[hour]['avg_pnl'] = stats_by_hour[hour]['total_pnl'] / stats_by_hour[hour]['count']
                stats_by_hour[hour]['avg_pnl_pct'] = stats_by_hour[hour]['total_pnl_pct'] / stats_by_hour[hour]['count']
                if len(stats_by_hour[hour]['wins']) > 0:
                    stats_by_hour[hour]['avg_win_pct'] = total_wins_pnl_pct / len(stats_by_hour[hour]['wins'])
                    wins_avg_underlying_price_change = sum(x['underlying_price_change'] for x in stats_by_hour[hour]['wins']) / len(stats_by_hour[hour]['wins'])
                    stats_by_hour[hour]['wins_avg_underlying_price_change'] = wins_avg_underlying_price_change
                if len(stats_by_hour[hour]['losses']) > 0:
                    stats_by_hour[hour]['avg_lose_pct'] = total_losses_pnl_pct / len(stats_by_hour[hour]['losses'])
                    losses_avg_underlying_price_change = avg_strike_delta = sum(x['underlying_price_change'] for x in stats_by_hour[hour]['losses']) / len(stats_by_hour[hour]['losses'])
                    stats_by_hour[hour]['losses_avg_underlying_price_change'] = losses_avg_underlying_price_change
        return stats_by_hour

    def get_close_position_stats(self, position):
        pnl = position.get_exit_pnl()
        pnl_pct = position.get_exit_pnl_pct()
        position_stats = {
            'pnl': pnl, 
            'pnl_pct': pnl_pct,
            'entry': position.opening_legs.get_total_fill_price(),
            'exit': position.closing_legs.get_total_fill_price(),
            'exit_reason': position.exit_reason,
            'underlying_on_entry': position.underlying_at_buy,
            'underlying_on_exit': position.underlying_at_sell,
            'underlying_price_change': 0,
            'leg_strikes': position.get_opening_legs_strikes_json()
        }
        if position.underlying_at_buy >= position.underlying_at_sell:
            position_stats['underlying_price_change'] = position.underlying_at_sell - position.underlying_at_buy
        else:
            position_stats['underlying_price_change'] = position.underlying_at_buy - position.underlying_at_sell
        return position_stats

    def get_high_mid_low_pnl(self, pos_stats_list):
        high = max(pos_stats_list, key=lambda x: x['pnl_pct'])
        # Lowest PnL%
        low = min(pos_stats_list, key=lambda x: x['pnl_pct'])

        from statistics import median
        mid = median([item['pnl_pct'] for item in pos_stats_list])

        return {
            'high': high, 'mid': mid, 'low': low
        }

