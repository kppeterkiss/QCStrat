import numpy as np

def calculate_trendlines(highs, lows):
    """Calculate upper and lower trendlines using linear regression"""
    x = np.arange(len(highs))
    upper_coef = np.polyfit(x, highs, 1)
    lower_coef = np.polyfit(x, lows, 1)
    
    upper_trendline = upper_coef[0] * x + upper_coef[1]
    lower_trendline = lower_coef[0] * x + lower_coef[1]
    
    return upper_trendline, lower_trendline

def calculate_support_resistance(prices, lookback_period=252, threshold=0.005):
    """Calculate support and resistance levels"""
    # Calculate recent support/resistance
    window = 20
    recent_support = min(prices[-window:])
    recent_resistance = max(prices[-window:])
    
    # Find historical levels from local maxima/minima
    historical_levels = {}
    lookback_prices = prices[-lookback_period:]
    
    # Find local maxima and minima
    for i in range(1, len(lookback_prices)-1):
        # Local maximum
        if lookback_prices[i] > lookback_prices[i-1] and lookback_prices[i] > lookback_prices[i+1]:
            level = lookback_prices[i]
            # Count touches within threshold
            touches = sum(1 for p in lookback_prices if abs(p - level)/level <= threshold)
            historical_levels[level] = touches
            
        # Local minimum 
        if lookback_prices[i] < lookback_prices[i-1] and lookback_prices[i] < lookback_prices[i+1]:
            level = lookback_prices[i]
            # Count touches within threshold
            touches = sum(1 for p in lookback_prices if abs(p - level)/level <= threshold)
            historical_levels[level] = touches
            
    return recent_support, recent_resistance, historical_levels

def calculate_fibonacci_levels(prices):
    """Calculate Fibonacci retracement levels"""
    high = max(prices)
    low = min(prices)
    diff = high - low
    
    levels = {
        0: low,
        0.236: low + 0.236 * diff,
        0.382: low + 0.382 * diff,
        0.5: low + 0.5 * diff,
        0.618: low + 0.618 * diff,
        1: high
    }
    return levels

def calculate_volume_confidence(volumes):
    """Calculate confidence based on volume analysis"""
    # Calculate volume ratio compared to average
    recent_vol_avg = np.mean(volumes[-5:])
    historical_vol_avg = np.mean(volumes)
    
    confidence = min(recent_vol_avg / historical_vol_avg, 1.0)
    return confidence 