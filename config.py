class Config:
    # API Configuration for Testnet
    API_KEY = "a8a877e475070f4daf24211ca07ddd9a95efc5aeeeae2b8bdeddb0da7740dd0b"
    API_SECRET = "cbd5ab54a2a619d56aa890c8d062eabe40fe61566e570a8d96d3d9511c89b081"
    
    # Trading Parameters
    SYMBOL = "BTCUSDT"
    TIMEFRAME = "1m"
    LEVERAGE = 5
    RISK_PERCENTAGE = 0.02  # 2% risk per trade
    
    # Use Testnet
    USE_TESTNET = True
    
    # Testnet URLs
    FUTURES_TESTNET_URL = 'https://testnet.binancefuture.com'
    
    # Technical Indicators Parameters
    KDJ_PERIOD = 9
    KDJ_M1 = 3
    KDJ_M2 = 3
    MA_PERIOD = 20
    RSI_PERIOD = 14
    BB_PERIOD = 20
    BB_STD = 2

    RECV_WINDOW = 5000  # 5 second window for requests
    MIN_TREND_STRENGTH = 0.5  # Minimum trend strength for entry
    STOP_LOSS = 0.02  # 2% stop loss
    PROFIT_TARGET = 0.03  # 3% take profit