from binance.client import Client
from utils import get_timestamp_with_offset
from config import Config
from indicators import TechnicalIndicators
from backtester import Backtester
import pandas as pd
from datetime import datetime
import time
from binance.enums import *
from binance.exceptions import BinanceAPIException

def format_server_time(timestamp_ms):
    """Convert millisecond timestamp to human readable format"""
    timestamp_s = timestamp_ms / 1000
    dt = datetime.fromtimestamp(timestamp_s)
    return dt.strftime('%Y-%m-%d %H:%M:%S')

def initialize_client():
    """Initialize Binance Testnet client for spot trading"""
    try:
        client = Client(
            Config.API_KEY,
            Config.API_SECRET,
            testnet=True
        )
        
        # Use spot testnet URL
        #client.API_URL = 'https://testnet.binance.vision'
        
        try:
            server_time = client.get_server_time()['serverTime']
            formatted_time = format_server_time(server_time)
            print(f"Server time: {formatted_time}")
            return client
        except BinanceAPIException as e:
            print(f"Error getting server time: {e}")
            raise
    except Exception as e:
        print(f"Error initializing client: {e}")
        raise

def get_historical_data(client: Client, symbol: str, interval: str, 
                       start_str: str, end_str: str = None) -> pd.DataFrame:
    """Fetch historical data from Binance Spot market"""
    try:
        start_ts = int(pd.Timestamp(start_str).timestamp() * 1000)
        end_ts = int(pd.Timestamp(end_str).timestamp() * 1000) if end_str else int(time.time() * 1000)
        
        # Use get_historical_klines for spot market
        klines = client.get_historical_klines(
            symbol=symbol,
            interval=interval,
            start_str=str(start_ts),
            end_str=str(end_ts),
            limit=1000
        )
        
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
        return df.set_index('timestamp')
        
    except Exception as e:
        print(f"Error fetching historical data: {e}")
        return pd.DataFrame()
def generate_trading_signal(k: float, d: float, rsi: float, 
                          current_price: float, ma: float, 
                          upper_bb: float, lower_bb: float,
                          trend_strength: float) -> dict:
    """
    Generate trading signals based on technical indicators
    Strategy combines KDJ crossover, RSI, and Bollinger Bands
    """
    signal = {
        'action': 'NEUTRAL',
        'confidence': 0,
        'reason': ''
    }
    
    # Strong trend condition
    if trend_strength < Config.MIN_TREND_STRENGTH:
        return signal
    
    # Buy Conditions
    if (k > d and  # KDJ bullish crossover
        rsi < 70 and  # Not overbought
        current_price < lower_bb and  # Price below lower BB
        current_price < ma):  # Price below MA
        
        signal['action'] = 'BUY'
        signal['confidence'] = min((70 - rsi) / 30 * trend_strength, 1)
        signal['reason'] = 'Bullish KDJ crossover with oversold RSI'
        
    # Sell Conditions    
    elif (k < d and  # KDJ bearish crossover
          rsi > 30 and  # Not oversold
          current_price > upper_bb and  # Price above upper BB
          current_price > ma):  # Price above MA
          
        signal['action'] = 'SELL'
        signal['confidence'] = min((rsi - 30) / 30 * trend_strength, 1)
        signal['reason'] = 'Bearish KDJ crossover with overbought RSI'
        
    return signal

def calculate_position_size(balance: float, current_price: float, 
                          signal_confidence: float) -> float:
    """
    Calculate position size based on:
    - Account balance
    - Risk percentage
    - Signal confidence
    """
    risk_amount = balance * Config.RISK_PERCENTAGE * signal_confidence
    position_size = risk_amount / (current_price * Config.STOP_LOSS)
    return position_size

def get_account_balance(client: Client) -> dict:
    """Get spot account balances"""
    try:
        account = client.get_account()
        balances = {}
        for asset in account['balances']:
            free_amount = float(asset['free'])
            locked_amount = float(asset['locked'])
            if free_amount > 0 or locked_amount > 0:
                balances[asset['asset']] = {
                    'free': free_amount,
                    'locked': locked_amount,
                    'total': free_amount + locked_amount
                }
        return balances
    except Exception as e:
        print(f"Error getting account balance: {e}")
        return {}

def place_trade(client: Client, signal: dict, current_price: float, 
                balance: float) -> dict:
    """Execute trade based on signal"""
    try:
        # Calculate position size
        usdt_balance = balance.get('USDT', {}).get('free', 0)
        position_size = calculate_position_size(
            usdt_balance, 
            current_price,
            signal['confidence']
        )
        
        if position_size * current_price < 10:  # Minimum order size check
            return None
            
        # Place market order
        order = place_order(
            client,
            Config.SYMBOL,
            signal['action'],
            position_size
        )
        
        if order:
            # Calculate stop-loss and take-profit prices
            stop_loss = current_price * (1 - Config.STOP_LOSS) if signal['action'] == 'BUY' \
                       else current_price * (1 + Config.STOP_LOSS)
                       
            take_profit = current_price * (1 + Config.PROFIT_TARGET) if signal['action'] == 'BUY' \
                         else current_price * (1 - Config.PROFIT_TARGET)
            
            # Place stop-loss order
            stop_loss_order = client.create_order(
                symbol=Config.SYMBOL,
                side='SELL' if signal['action'] == 'BUY' else 'BUY',
                type=ORDER_TYPE_STOP_LOSS_LIMIT,
                quantity=position_size,
                price=stop_loss,
                stopPrice=stop_loss
            )
            
            return {
                'entry_order': order,
                'stop_loss': stop_loss_order,
                'take_profit': take_profit
            }
            
    except Exception as e:
        print(f"Error placing trade: {e}")
        return None

def place_order(client: Client, symbol: str, side: str, quantity: float):
    """Place spot market order"""
    try:
        # Get symbol info for precision
        symbol_info = client.get_symbol_info(symbol)
        step_size = None
        
        # Find the step size for quantity
        for f in symbol_info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                step_size = float(f['stepSize'])
                break
                
        # Round quantity to the correct precision
        if step_size:
            quantity = round(quantity - (quantity % step_size), len(str(step_size).split('.')[1]))
        
        order = client.create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=quantity
        )
        
        print(f"Placed {side} order: {order}")
        return order
        
    except Exception as e:
        print(f"Error placing order: {e}")
        return None

def get_current_price(client: Client, symbol: str) -> float:
    """Get current price for a symbol"""
    try:
        ticker = client.get_symbol_ticker(symbol=symbol)
        return float(ticker['price'])
    except Exception as e:
        print(f"Error getting current price: {e}")
        return None

def run_live_trading():
    """Run live spot trading strategy"""
    try:
        client = initialize_client()
        print("Successfully connected to Binance Testnet (Spot)")
        
        indicators = TechnicalIndicators()
        start_time = (datetime.now() - pd.Timedelta(days=1)).strftime('%Y-%m-%d')
        
        active_position = False
        
        while True:
            try:
                # Get latest data
                df = get_historical_data(
                    client, 
                    Config.SYMBOL, 
                    Config.TIMEFRAME,
                    start_str=start_time
                )
                
                if df.empty:
                    print("No data received, waiting...")
                    time.sleep(10)
                    continue
                
                # Get market data
                balances = get_account_balance(client)
                current_price = get_current_price(client, Config.SYMBOL)
                current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Calculate indicators
                k, d, trend_strength = indicators.calculate_KDJ(df)
                rsi = indicators.calculate_RSI(df)
                ma, upper_bb, lower_bb = indicators.calculate_bollinger_bands(df)
                
                # Generate trading signal
                signal = generate_trading_signal(
                    k, d, rsi, current_price, ma, 
                    upper_bb, lower_bb, trend_strength
                )
                
                # Print market information
                print(f"\nTime: {current_time}")
                print(f"Price: ${current_price:,.2f}")
                print(f"Signal: {signal['action']} (Confidence: {signal['confidence']:.2f})")
                print(f"Reason: {signal['reason']}")
                print("\nIndicators:")
                print(f"KDJ - K: {k:.2f}, D: {d:.2f}")
                print(f"RSI: {rsi:.2f}")
                print(f"BB: {lower_bb:.2f} < {ma:.2f} < {upper_bb:.2f}")
                
                # Execute trading logic
                if not active_position and signal['action'] in ['BUY', 'SELL']:
                    trade_result = place_trade(client, signal, current_price, balances)
                    if trade_result:
                        active_position = True
                        print(f"\nExecuted {signal['action']} trade:")
                        print(f"Entry Price: ${current_price:,.2f}")
                        print(f"Stop Loss: ${trade_result['stop_loss']:,.2f}")
                        print(f"Take Profit: ${trade_result['take_profit']:,.2f}")
                
                time.sleep(Config.INTERVAL)
                
            except Exception as e:
                print(f"Error in trading loop: {e}")
                time.sleep(Config.INTERVAL)
                
    except Exception as e:
        print(f"Critical error in trading: {e}")

if __name__ == "__main__":
    print("=== Crypto Spot Trading Bot (Testnet) ===")
    print("1. Run Live Trading")
    print("2. Show Current Price")
    print("3. Show Account Balance")
    
    choice = input("Enter your choice (1-3): ")
    
    try:
        client = initialize_client()
        
        if choice == "1":
            print("Starting spot trading...")
            run_live_trading()
        elif choice == "2":
            price = get_current_price(client, Config.SYMBOL)
            print(f"Current {Config.SYMBOL} price: ${price:,.2f}")
        elif choice == "3":
            balances = get_account_balance(client)
            print("\nAccount Balances:")
            for asset, balance in balances.items():
                print(f"{asset}: {balance['free']} (Free) / {balance['locked']} (Locked)")
        else:
            print("Invalid choice!")
    except Exception as e:
        print(f"Fatal error: {e}")