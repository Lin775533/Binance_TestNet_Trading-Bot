# indicators.py
import pandas as pd
import numpy as np
from typing import Tuple, Dict

class TechnicalIndicators:
    @staticmethod
    def calculate_KDJ(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> Tuple[float, float, float]:
        """Calculate KDJ indicator with trend strength"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        lowest_low = low.rolling(window=n, min_periods=1).min()
        highest_high = high.rolling(window=n, min_periods=1).max()
        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
        
        K = pd.Series(index=rsv.index)
        D = pd.Series(index=rsv.index)
        K.iloc[0] = 50
        D.iloc[0] = 50
        
        for i in range(1, len(rsv)):
            K.iloc[i] = (2/3) * K.iloc[i-1] + (1/3) * rsv.iloc[i]
            D.iloc[i] = (2/3) * D.iloc[i-1] + (1/3) * K.iloc[i]
        
        J = 3 * K - 2 * D
        trend_strength = abs(K - D) / (0.1 + J.rolling(5).std())
        
        return K.iloc[-1], D.iloc[-1], trend_strength.iloc[-1]

    @staticmethod
    def calculate_RSI(df: pd.DataFrame, period: int = 14) -> float:
        """Calculate RSI indicator"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std: int = 2) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands"""
        ma = df['close'].rolling(window=period).mean()
        std_dev = df['close'].rolling(window=period).std()
        upper_band = ma + (std_dev * std)
        lower_band = ma - (std_dev * std)
        return ma.iloc[-1], upper_band.iloc[-1], lower_band.iloc[-1]

    @staticmethod
    def calculate_volume_profile(df: pd.DataFrame, num_bins: int = 10) -> Dict[float, float]:
        """Calculate Volume Profile"""
        price_range = np.linspace(df['low'].min(), df['high'].max(), num_bins)
        volume_profile = pd.cut(df['close'], bins=price_range).value_counts() * df['volume'].mean()
        return dict(zip(price_range[1:], volume_profile))

    @staticmethod
    def calculate_support_resistance(df: pd.DataFrame, lookback: int = 20, threshold: float = 0.02) -> Tuple[float, float]:
        """Calculate Dynamic Support and Resistance levels"""
        highs = df['high'].rolling(window=lookback).max()
        lows = df['low'].rolling(window=lookback).min()
        
        # Find clusters of highs and lows
        price_range = df['close'].iloc[-1] * threshold
        resistance = highs.value_counts().sort_index().iloc[-1]
        support = lows.value_counts().sort_index().iloc[0]
        
        return support, resistance
