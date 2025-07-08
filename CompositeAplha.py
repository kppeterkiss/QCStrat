from QuantConnect.Algorithm.Framework.Alphas import *
from QuantConnect.Algorithm.Framework.Portfolio import *
from datetime import timedelta, datetime
import numpy as np
import pandas as pd
from enum import Enum
import talib
class IndicatorStrength:
    def __init__(self, lookback_period=30*24):  # 30 days * 24 hours for hourly data
        self.lookback_period = lookback_period
        self.indicators = {}
        self.signals = []
        
    class IndicatorStats:
        def __init__(self):
            self.true_positives = 0  # Correct predictions
            self.false_positives = 0  # Wrong predictions
            self.total_signals = 0
            self.cumulative_return = 0  # For signals that triggered
            self.alpha = 0  # Risk-adjusted excess return
            self.beta = 0  # Market correlation
            self.signal_returns = []  # Store returns for each signal
            
    def record_signal(self, timestamp, indicator_name, direction, price):
        """Record a new signal from an indicator"""
        if indicator_name not in self.indicators:
            self.indicators[indicator_name] = self.IndicatorStats()
            
        self.signals.append({
            'timestamp': timestamp,
            'indicator': indicator_name,
            'direction': direction,
            'entry_price': price,
            'evaluated': False
        })
        
        self.indicators[indicator_name].total_signals += 1
        
        # Remove signals older than lookback period
        cutoff_time = timestamp - timedelta(hours=self.lookback_period)
        self.signals = [s for s in self.signals if s['timestamp'] > cutoff_time]
        
    def evaluate_signals(self, current_time, current_price, market_return):
        """Evaluate previous signals and update indicator statistics"""
        for signal in self.signals:
            if signal['evaluated']:
                continue
                
            # Only evaluate signals that are at least 1 period old
            if (current_time - signal['timestamp']).total_seconds() < 3600:
                continue
                
            signal['evaluated'] = True
            indicator = self.indicators[signal['indicator']]
            
            # Calculate return
            signal_return = (current_price - signal['entry_price']) / signal['entry_price']
            if signal['direction'] == 'bearish':
                signal_return = -signal_return
                
            indicator.signal_returns.append(signal_return)
            
            # Update statistics
            if signal_return > 0:
                indicator.true_positives += 1
            else:
                indicator.false_positives += 1
                
            indicator.cumulative_return += signal_return
            
            # Calculate alpha and beta
            if len(indicator.signal_returns) > 1:
                returns = np.array(indicator.signal_returns)
                market_returns = np.array(market_return[-len(returns):])
                
                # Beta = covariance(signal, market) / variance(market)
                beta = np.cov(returns, market_returns)[0,1] / np.var(market_returns)
                
                # Alpha = average signal return - beta * average market return
                alpha = np.mean(returns) - (beta * np.mean(market_returns))
                
                indicator.alpha = alpha
                indicator.beta = beta
                
    def get_indicator_metrics(self, indicator_name):
        """Get current statistics for an indicator"""
        if indicator_name not in self.indicators:
            return None
            
        ind = self.indicators[indicator_name]
        accuracy = ind.true_positives / ind.total_signals if ind.total_signals > 0 else 0
        
        return {
            'accuracy': accuracy,
            'total_signals': ind.total_signals,
            'cumulative_return': ind.cumulative_return,
            'alpha': ind.alpha,
            'beta': ind.beta
        }

class TechnicalIndicatorAlphaModel:
    def __init__(self):
        self.symbolData = {}
        self.resolution = Resolution.Hour
        self.period = 20
        self.rebalancingPeriod = timedelta(hours=1)
        self.nextRebalance = datetime.min
        
    class SymbolData:
        def __init__(self, algorithm, symbol):
            self.symbol = symbol
            self.algorithm = algorithm
            self.window = RollingWindow[TradeBar](200)
            self.consolidator = TradeBarConsolidator(timedelta(hours=1))
            self.consolidator.DataConsolidated += self.OnDataConsolidated
            algorithm.SubscriptionManager.AddConsolidator(symbol, self.consolidator)
            
        def OnDataConsolidated(self, sender, bar):
            self.window.Add(bar)
            
    def Update(self, algorithm, data):
        # Initialize empty lists for triggered patterns
        triggered_bullish = []
        triggered_bearish = []
        
        # These will be populated with actual triggered patterns
        # when patterns are detected in detect_candlestick_patterns()
        # and other technical analysis methods
        if algorithm.Time <= self.nextRebalance:
            return []
            
        self.nextRebalance = algorithm.Time + self.rebalancingPeriod
        
        insights = []
        for symbol, symbolData in self.symbolData.items():
            if not symbolData.window.IsReady:
                continue
                
            # Get price data
            prices = np.array([bar.Close for bar in reversed(symbolData.window)])
            highs = np.array([bar.High for bar in reversed(symbolData.window)])
            lows = np.array([bar.Low for bar in reversed(symbolData.window)])
            volumes = np.array([bar.Volume for bar in reversed(symbolData.window)])
            
            # Calculate trendlines
            upper_trendline, lower_trendline = self.calculate_trendlines(highs, lows)
            
            # Calculate support and resistance
            support, resistance = self.calculate_support_resistance(prices)
            
            # Calculate Fibonacci levels
            fib_levels = self.calculate_fibonacci_levels(prices)
            
            # Detect candlestick patterns
            patterns = self.detect_candlestick_patterns(highs, lows, prices)
            
            # Calculate confidence based on volume
            confidence = self.calculate_volume_confidence(volumes)
            
            # Generate insights based on technical indicators
            current_price = prices[-1]
            
            # Determine direction based on all indicators
            bullish_signals = 0
            bearish_signals = 0
            
            # Initialize lists to track which signals triggered
            triggered_bullish = []
            triggered_bearish = []
            
            # Check trendlines
            if current_price > upper_trendline[-1]:
                bullish_signals += 1
                triggered_bullish.append("Above upper trendline")
            elif current_price < lower_trendline[-1]:
                bearish_signals += 1
                triggered_bearish.append("Below lower trendline")
                
            # Check trendline pullbacks and bounces
            trendline_threshold = 0.02  # 2% threshold
            price_history = prices[-5:]  # Look at last 5 periods
            
            # Bullish pullback to lower trendline
            if (abs(current_price - lower_trendline[-1]) / current_price < trendline_threshold and
                prices[-2] < lower_trendline[-2]):  # Price crossing back above trendline
                bullish_signals += 1
                triggered_bullish.append("Bullish pullback to lower trendline")
                # Check for bounce
                if min(price_history) < lower_trendline[-1] and current_price > lower_trendline[-1]:
                    bullish_signals += 1  # Add extra signal for confirmed bounce
                    triggered_bullish.append("Confirmed bounce from lower trendline")
                    
            # Bearish pullback to upper trendline    
            if (abs(current_price - upper_trendline[-1]) / current_price < trendline_threshold and
                prices[-2] > upper_trendline[-2]):  # Price crossing back below trendline
                bearish_signals += 1
                triggered_bearish.append("Bearish pullback to upper trendline")
                # Check for bounce
                if max(price_history) > upper_trendline[-1] and current_price < upper_trendline[-1]:
                    bearish_signals += 1  # Add extra signal for confirmed bounce
                    triggered_bearish.append("Confirmed bounce from upper trendline")
                
            # Check support/resistance
            if current_price < resistance and current_price > support:
                if abs(current_price - resistance) < abs(current_price - support):
                    bearish_signals += 1
                    triggered_bearish.append("Closer to resistance than support")
                else:
                    bullish_signals += 1
                    triggered_bullish.append("Closer to support than resistance")
                    
            # Check for support/resistance pullbacks and bounces
            short_ma = np.mean(prices[-5:])  # 5-period moving average
            long_ma = np.mean(prices[-20:])  # 20-period moving average
            
            # Bullish pullback: Price pulls back to support in uptrend
            if long_ma > short_ma and current_price > long_ma:
                if abs(current_price - support) / current_price < 0.02:  # Within 2% of support
                    bullish_signals += 1
                    triggered_bullish.append("Bullish pullback to support in uptrend")
                    # Check for bounce from support
                    if min(price_history) <= support and current_price > support:
                        bullish_signals += 1
                        triggered_bullish.append("Confirmed bounce from support")
                    
            # Bearish pullback: Price pulls back to resistance in downtrend  
            if long_ma < short_ma and current_price < long_ma:
                if abs(current_price - resistance) / current_price < 0.02:  # Within 2% of resistance
                    bearish_signals += 1
                    triggered_bearish.append("Bearish pullback to resistance in downtrend")
                    # Check for bounce from resistance
                    if max(price_history) >= resistance and current_price < resistance:
                        bearish_signals += 1
                        triggered_bearish.append("Confirmed bounce from resistance")
                    
            # Check candlestick patterns
            if patterns['bullish_engulfing']:
                bullish_signals += 1
                triggered_bullish.append("Bullish engulfing pattern")
            if patterns['bearish_engulfing']:
                bearish_signals += 1
                triggered_bearish.append("Bearish engulfing pattern")
            if patterns['bullish_harami'] or patterns['bullish_harami_cross']:
                bullish_signals += 1
                triggered_bullish.append("Bullish harami pattern")
            if patterns['bearish_harami'] or patterns['bearish_harami_cross']:
                bearish_signals += 1
                triggered_bearish.append("Bearish harami pattern")
            if patterns['piercing_line']:
                bullish_signals += 1
                triggered_bullish.append("Piercing line pattern")
            if patterns['head_and_shoulders']:
                bearish_signals += 1
                triggered_bearish.append("Head and shoulders pattern")
            if patterns['bull_flag']:
                bullish_signals += 1
                triggered_bullish.append("Bull flag pattern")
            if patterns['ascending_triangle']:
                bullish_signals += 1
                triggered_bullish.append("Ascending triangle pattern")
            if patterns['descending_triangle']:
                bearish_signals += 1
                triggered_bearish.append("Descending triangle pattern")
            if patterns['rising_wedge']:
                bearish_signals += 1  # Rising wedge is typically bearish
                triggered_bearish.append("Rising wedge pattern")
            if patterns['falling_wedge']:
                bullish_signals += 1  # Falling wedge is typically bullish
                triggered_bullish.append("Falling wedge pattern")
            if patterns['cup_and_handle']:
                bullish_signals += 1
                triggered_bullish.append("Cup and handle pattern")
            if patterns['megaphone']:
                # Megaphone can be either bullish or bearish depending on context
                if current_price > prices[-2]:  # Using price action to determine direction
                    bullish_signals += 1
                    triggered_bullish.append("Bullish megaphone pattern")
                else:
                    bearish_signals += 1
                    triggered_bearish.append("Bearish megaphone pattern")
            if patterns['pennant']:
                # Pennant follows the prior trend
                if current_price > prices[-10]:  # Check if uptrend
                    bullish_signals += 1
                    triggered_bullish.append("Bullish pennant pattern")
                else:
                    bearish_signals += 1
                    triggered_bearish.append("Bearish pennant pattern")
                
            # Generate insight if signals are strong enough
            if bullish_signals > bearish_signals:
                magnitude = min(abs(resistance - current_price) / current_price,
                             abs(upper_trendline[-1] - current_price) / current_price)
                insights.append(Insight.Price(
                    symbol, timedelta(days=1), InsightDirection.Up,
                    magnitude, confidence))
                    
            elif bearish_signals > bullish_signals:
                magnitude = min(abs(support - current_price) / current_price,
                             abs(lower_trendline[-1] - current_price) / current_price)
                insights.append(Insight.Price(
                    symbol, timedelta(days=1), InsightDirection.Down,
                    magnitude, confidence))
                    
        return insights
        
    def OnSecuritiesChanged(self, algorithm, changes):
        for removed in changes.RemovedSecurities:
            if removed.Symbol in self.symbolData:
                consolidator = self.symbolData[removed.Symbol].consolidator
                algorithm.SubscriptionManager.RemoveConsolidator(removed.Symbol, consolidator)
                del self.symbolData[removed.Symbol]

        for added in changes.AddedSecurities:
            if added.Symbol not in self.symbolData:
                self.symbolData[added.Symbol] = self.SymbolData(algorithm, added.Symbol)
                
    def calculate_trendlines(self, highs, lows):
        x = np.arange(len(highs))
        upper_coef = np.polyfit(x, highs, 1)
        lower_coef = np.polyfit(x, lows, 1)
        
        upper_trendline = upper_coef[0] * x + upper_coef[1]
        lower_trendline = lower_coef[0] * x + lower_coef[1]
        
        return upper_trendline, lower_trendline
        
    def calculate_support_resistance(self, prices, lookback_period=252, threshold=0.005):
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

        
    def calculate_fibonacci_levels(self, prices):
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
        
    def detect_candlestick_patterns(self, highs, lows, closes, opens):
        patterns = {}
        
        # Single candlestick patterns
        # Doji
        body = abs(closes[-1] - opens[-1])
        wick = highs[-1] - max(opens[-1], closes[-1])
        tail = min(opens[-1], closes[-1]) - lows[-1]
        if body <= 0.1 * (highs[-1] - lows[-1]):
            patterns['doji'] = True
            # Dragonfly doji
            if wick <= 0.1 * (highs[-1] - lows[-1]) and tail >= 0.7 * (highs[-1] - lows[-1]):
                patterns['dragonfly_doji'] = True
            # Gravestone doji
            if wick >= 0.7 * (highs[-1] - lows[-1]) and tail <= 0.1 * (highs[-1] - lows[-1]):
                patterns['gravestone_doji'] = True

        # Hammer
        if tail >= 2 * body and wick <= 0.1 * (highs[-1] - lows[-1]):
            patterns['hammer'] = True

        # Inverted Hammer
        if wick >= 2 * body and tail <= 0.1 * (highs[-1] - lows[-1]):
            patterns['inverted_hammer'] = True

        # Shooting Star
        if wick >= 2 * body and tail <= body and opens[-1] < closes[-1]:
            patterns['shooting_star'] = True

        # Spinning Top
        if 0.3 <= body/(highs[-1] - lows[-1]) <= 0.7:
            patterns['spinning_top'] = True

        # Marubozu
        if wick <= 0.1 * body and tail <= 0.1 * body:
            patterns['bearish_marubozu'] = closes[-1] < opens[-1]

        # Two candlestick patterns
        # Bullish Engulfing
        if closes[-1] > opens[-1] and opens[-1] < closes[-2] and closes[-1] > opens[-2] and opens[-2] > closes[-2]:
            patterns['bullish_engulfing'] = True

        # Bearish Engulfing
        if closes[-1] < opens[-1] and opens[-1] > closes[-2] and closes[-1] < opens[-2] and opens[-2] < closes[-2]:
            patterns['bearish_engulfing'] = True

        # Bullish Harami
        if closes[-2] < opens[-2] and opens[-1] > closes[-1] and \
           opens[-1] <= closes[-2] and closes[-1] >= opens[-2]:
            patterns['bullish_harami'] = True
            # Bullish Harami Cross
            if abs(opens[-1] - closes[-1]) <= 0.1 * (highs[-1] - lows[-1]):
                patterns['bullish_harami_cross'] = True

        # Bearish Harami
        if closes[-2] > opens[-2] and opens[-1] < closes[-1] and \
           opens[-1] >= closes[-2] and closes[-1] <= opens[-2]:
            patterns['bearish_harami'] = True
            # Bearish Harami Cross
            if abs(opens[-1] - closes[-1]) <= 0.1 * (highs[-1] - lows[-1]):
                patterns['bearish_harami_cross'] = True

        # Piercing Line
        if closes[-2] < opens[-2] and closes[-1] > opens[-1] and \
           opens[-1] < lows[-2] and closes[-1] > (opens[-2] + closes[-2])/2:
            patterns['piercing_line'] = True

        # Chart Patterns (requires more historical data)
        if len(highs) >= 20:
            # Head and Shoulders
            left_shoulder = max(highs[-20:-15])
            head = max(highs[-15:-10])
            right_shoulder = max(highs[-10:-5])
            if head > left_shoulder and head > right_shoulder and \
               abs(left_shoulder - right_shoulder)/left_shoulder < 0.02:
                patterns['head_and_shoulders'] = True

            # Bull Flag
            if all(highs[i] < highs[i-1] for i in range(-1, -6, -1)) and \
               all(lows[i] < lows[i-1] for i in range(-1, -6, -1)):
                patterns['bull_flag'] = True

            # Ascending Triangle
            resistance = max(highs[-20:])
            if all(lows[i] > lows[i-1] for i in range(-1, -10, -1)) and \
               all(abs(highs[i] - resistance) < 0.02 * resistance for i in range(-1, -10, -1)):
                patterns['ascending_triangle'] = True

            # Descending Triangle
            support = min(lows[-20:])
            if all(highs[i] < highs[i-1] for i in range(-1, -10, -1)) and \
               all(abs(lows[i] - support) < 0.02 * support for i in range(-1, -10, -1)):
                patterns['descending_triangle'] = True

            # Rising Wedge
            if all(highs[i] > highs[i-1] for i in range(-1, -10, -1)) and \
               all(lows[i] > lows[i-1] for i in range(-1, -10, -1)):
                patterns['rising_wedge'] = True

            # Falling Wedge
            if all(highs[i] < highs[i-1] for i in range(-1, -10, -1)) and \
               all(lows[i] < lows[i-1] for i in range(-1, -10, -1)):
                patterns['falling_wedge'] = True

            # Cup and Handle
            cup_bottom = min(lows[-20:-10])
            if all(lows[i] > cup_bottom for i in range(-9, -1)):
                patterns['cup_and_handle'] = True

            # Megaphone
            if all(highs[i] > highs[i-1] for i in range(-1, -10, -1)) and \
               all(lows[i] < lows[i-1] for i in range(-1, -10, -1)):
                patterns['megaphone'] = True

            # Pennant
            if all(highs[i] < highs[i-1] for i in range(-1, -10, -1)) and \
               all(lows[i] > lows[i-1] for i in range(-1, -10, -1)):
                patterns['pennant'] = True

        return patterns
    def calculate_volume_confidence(self, volumes):
        # Calculate volume ratio compared to average
        recent_vol_avg = np.mean(volumes[-5:])
        historical_vol_avg = np.mean(volumes)
        
        confidence = min(recent_vol_avg / historical_vol_avg, 1.0)
        return confidence

class PortfolioConstructionModel:
    def __init__(self):
        self.positions = {}
        
    def CreateTargets(self, algorithm, insights):
        targets = []
        
        # Group insights by symbol
        grouped_insights = {}
        for insight in insights:
            if insight.Symbol not in grouped_insights:
                grouped_insights[insight.Symbol] = []
            grouped_insights[insight.Symbol].append(insight)
            
        for symbol, symbol_insights in grouped_insights.items():
            # Check if all insights agree on direction
            directions = [insight.Direction for insight in symbol_insights]
            
            if symbol not in self.positions:
                # No position exists, check for new position
                if all(d == directions[0] for d in directions):
                    targets.append(PortfolioTarget(symbol, 1 if directions[0] == InsightDirection.Up else -1))
                    self.positions[symbol] = directions[0]
            else:
                # Position exists, check if majority of insights changed direction
                current_direction = self.positions[symbol]
                opposite_direction = InsightDirection.Up if current_direction == InsightDirection.Down else InsightDirection.Down
                
                if sum(1 for d in directions if d == opposite_direction) > len(directions) / 2:
                    targets.append(PortfolioTarget(symbol, 0))
                    del self.positions[symbol]
                    
        return targets

class TradingAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2020, 1, 1)
        self.SetCash(100000)
        
        # Add symbols
        self.symbol = self.AddEquity("SPY", Resolution.Hour).Symbol
        
        # Set up alpha model
        self.SetAlpha(TechnicalIndicatorAlphaModel())
        
        # Set up portfolio construction model
        self.SetPortfolioConstruction(PortfolioConstructionModel())
        
        # Set up plotting
        self.Plot.SetEnabled(True)
        
    def OnData(self, data):
        if not self.Portfolio[self.symbol].Invested:
            self.Plot("Trade Signals", "Entry", self.Securities[self.symbol].Close)
        else:
            self.Plot("Trade Signals", "Exit", self.Securities[self.symbol].Close)
            
        # Plot technical indicators
        if self.symbol in data:
            bar = data[self.symbol]
            self.Plot("Price", "Close", bar.Close)
            self.Plot("Volume", "Volume", bar.Volume)
