# utils.py
import pandas as pd
import numpy as np
from typing import Dict, List
import logging
from datetime import datetime
# In utils.py, add this import at the top
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_bot.log'),
        logging.StreamHandler()
    ]
)

def setup_logger():
    """Setup logger for the trading bot"""
    return logging.getLogger('trading_bot')

def calculate_trade_metrics(trades: List[Dict]) -> Dict:
    """Calculate comprehensive trade metrics"""
    if not trades:
        return {}

    profits = [trade['profit'] for trade in trades]
    durations = [(trade['exit_time'] - trade['entry_time']).total_seconds()/3600 
                 for trade in trades]

    metrics = {
        'total_trades': len(trades),
        'winning_trades': len([p for p in profits if p > 0]),
        'losing_trades': len([p for p in profits if p < 0]),
        'win_rate': len([p for p in profits if p > 0]) / len(trades),
        'average_profit': np.mean(profits),
        'median_profit': np.median(profits),
        'largest_win': max(profits),
        'largest_loss': min(profits),
        'average_duration': np.mean(durations),
        'profit_factor': abs(sum([p for p in profits if p > 0]) / 
                           sum([p for p in profits if p < 0])) if sum([p for p in profits if p < 0]) != 0 else float('inf'),
        'expectancy': np.mean(profits) / np.std(profits) if len(profits) > 1 else 0
    }
    
    return metrics
def get_timestamp_with_offset(offset: int) -> int:
    """Get current timestamp with server offset applied"""
    return int(time.time() * 1000) + offset

def format_number(number: float, decimals: int = 8) -> str:
    """Format number with appropriate decimal places"""
    return f"{number:.{decimals}f}"

def calculate_risk_reward_ratio(entry_price: float, stop_loss: float, 
                              take_profit: float, side: str) -> float:
    """Calculate risk/reward ratio for a trade"""
    if side == 'long':
        risk = entry_price - stop_loss
        reward = take_profit - entry_price
    else:
        risk = stop_loss - entry_price
        reward = entry_price - take_profit
    
    return reward / risk if risk != 0 else 0

def validate_price_data(df: pd.DataFrame) -> bool:
    """Validate price data for integrity"""
    # Check for required columns
    required_columns = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    if not all(col in df.columns for col in required_columns):
        return False
    
    # Check for missing values
    if df[required_columns].isnull().any().any():
        return False
    
    # Check for logical price relationships
    price_valid = (df['high'] >= df['low']).all() and \
                 (df['high'] >= df['close']).all() and \
                 (df['high'] >= df['open']).all() and \
                 (df['low'] <= df['close']).all() and \
                 (df['low'] <= df['open']).all()
    
    return price_valid

def calculate_drawdown(equity_curve: pd.Series) -> pd.Series:
    """Calculate drawdown series"""
    rolling_max = equity_curve.expanding(min_periods=1).max()
    drawdown = equity_curve / rolling_max - 1
    return drawdown

def save_trade_history(trades: List[Dict], filename: str = 'trade_history.csv'):
    """Save trade history to CSV file"""
    if not trades:
        return
        
    df = pd.DataFrame(trades)
    df.to_csv(filename, index=False)
    logging.info(f"Trade history saved to {filename}")

def load_trade_history(filename: str = 'trade_history.csv') -> List[Dict]:
    """Load trade history from CSV file"""
    try:
        df = pd.DataFrame(filename)
        return df.to_dict('records')
    except Exception as e:
        logging.error(f"Error loading trade history: {e}")
        return []
