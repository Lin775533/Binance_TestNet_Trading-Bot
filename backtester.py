# backtester.py
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict
from indicators import TechnicalIndicators

class Backtester:
    def __init__(self, df: pd.DataFrame, initial_balance: float = 10000):
        self.df = df
        self.balance = initial_balance
        self.positions: List[Dict] = []
        self.trades_history: List[Dict] = []
        self.indicators = TechnicalIndicators()

    def calculate_metrics(self) -> Dict:
        """Calculate trading metrics from backtest results"""
        if not self.trades_history:
            return {}

        profits = [trade['profit'] for trade in self.trades_history]
        winning_trades = [p for p in profits if p > 0]
        losing_trades = [p for p in profits if p < 0]

        metrics = {
            'total_trades': len(self.trades_history),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(self.trades_history) if self.trades_history else 0,
            'average_profit': np.mean(profits) if profits else 0,
            'max_drawdown': self.calculate_max_drawdown(),
            'sharpe_ratio': self.calculate_sharpe_ratio(),
            'final_balance': self.balance
        }
        return metrics

    def calculate_max_drawdown(self) -> float:
        """Calculate maximum drawdown"""
        balance_history = [trade['balance_after'] for trade in self.trades_history]
        peak = balance_history[0]
        max_drawdown = 0
        
        for balance in balance_history:
            if balance > peak:
                peak = balance
            drawdown = (peak - balance) / peak
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown

    def calculate_sharpe_ratio(self) -> float:
        """Calculate Sharpe Ratio"""
        if not self.trades_history:
            return 0
            
        returns = [trade['profit']/trade['balance_before'] for trade in self.trades_history]
        if not returns:
            return 0
            
        return np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252)

    def run_backtest(self, strategy_config: Dict) -> Dict:
        """Run backtest with given strategy configuration"""
        for i in range(len(self.df)-1):
            current_data = self.df.iloc[:i+1]
            
            # Calculate indicators
            k, d, trend_strength = self.indicators.calculate_KDJ(current_data)
            rsi = self.indicators.calculate_RSI(current_data)
            ma, upper_bb, lower_bb = self.indicators.calculate_bollinger_bands(current_data)
            support, resistance = self.indicators.calculate_support_resistance(current_data)
            
            # Check for entry signals
            if not self.positions:  # No open positions
                if self.check_entry_signal(k, d, rsi, current_data['close'].iloc[-1], 
                                        ma, upper_bb, lower_bb, trend_strength, strategy_config):
                    self.open_position(current_data, strategy_config)
            
            # Check for exit signals
            else:
                if self.check_exit_signal(self.positions[-1], current_data, strategy_config):
                    self.close_position(current_data)
        
        return self.calculate_metrics()

    def check_entry_signal(self, k: float, d: float, rsi: float, price: float, 
                          ma: float, upper_bb: float, lower_bb: float, 
                          trend_strength: float, config: Dict) -> bool:
        """Check entry conditions"""
        # Long entry conditions
        if (k > d and  # KDJ crossover
            rsi < 30 and  # Oversold RSI
            price > ma and  # Price above MA
            trend_strength > config['min_trend_strength'] and  # Strong trend
            price < lower_bb):  # Price below lower BB
            return True
            
        # Short entry conditions
        if (k < d and  # KDJ crossunder
            rsi > 70 and  # Overbought RSI
            price < ma and  # Price below MA
            trend_strength > config['min_trend_strength'] and  # Strong trend
            price > upper_bb):  # Price above upper BB
            return True
            
        return False

    def check_exit_signal(self, position: Dict, current_data: pd.DataFrame, config: Dict) -> bool:
        """Check exit conditions"""
        current_price = current_data['close'].iloc[-1]
        entry_price = position['entry_price']
        
        # Check stop loss
        if position['side'] == 'long':
            if current_price <= entry_price * (1 - config['stop_loss']):
                return True
        else:
            if current_price >= entry_price * (1 + config['stop_loss']):
                return True
                
        # Check take profit
        if position['side'] == 'long':
            if current_price >= entry_price * (1 + config['profit_target']):
                return True
        else:
            if current_price <= entry_price * (1 - config['profit_target']):
                return True
                
        return False
