from datetime import timedelta, datetime
import numpy as np
from QuantConnect.Algorithm.Framework.Alphas import AlphaModel, Insight, InsightDirection, InsightType
from QuantConnect.Data.Market import TradeBar
from QuantConnect.Indicators.CandlestickPatterns import *

from ..indicators.indicator_strength import IndicatorStrength
from ..indicators.technical_indicators import (
    calculate_trendlines,
    calculate_support_resistance,
    calculate_fibonacci_levels,
    calculate_volume_confidence
)
from ..indicators.candlestick_patterns import detect_candlestick_patterns

class TechnicalIndicatorAlphaModel(AlphaModel):
    def __init__(self):
        super().__init__()
        self.symbolData = {}
        self.resolution = Resolution.Hour
        self.period = 20
        self.rebalancingPeriod = timedelta(hours=1)
        self.nextRebalance = datetime.min
        self.indicator_strength = IndicatorStrength()
        
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
            opens = np.array([bar.Open for bar in reversed(symbolData.window)])
            
            # Calculate indicators
            upper_trendline, lower_trendline = calculate_trendlines(highs, lows)
            support, resistance, historical_levels = calculate_support_resistance(prices)
            fib_levels = calculate_fibonacci_levels(prices)
            patterns = detect_candlestick_patterns(highs, lows, closes, opens)
            confidence = calculate_volume_confidence(volumes)
            
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
                    magnitude, confidence, sourceModel="TechnicalIndicatorAlphaModel"))
                    
            elif bearish_signals > bullish_signals:
                magnitude = min(abs(support - current_price) / current_price,
                             abs(lower_trendline[-1] - current_price) / current_price)
                insights.append(Insight.Price(
                    symbol, timedelta(days=1), InsightDirection.Down,
                    magnitude, confidence, sourceModel="TechnicalIndicatorAlphaModel"))
                    
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