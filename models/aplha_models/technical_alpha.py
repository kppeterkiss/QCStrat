from datetime import timedelta, datetime
import numpy as np
from QuantConnect.Algorithm.Framework.Alphas import AlphaModel, Insight, InsightDirection, InsightType
from QuantConnect.Data.Market import TradeBar
from QuantConnect.Indicators.CandlestickPatterns import *

from indicators.indicator_strength import IndicatorStrength
from indicators.technical_indicators import (
    calculate_trendlines,
    calculate_support_resistance,
    calculate_fibonacci_levels,
    calculate_volume_confidence
)
from indicators.candlestick_patterns import detect_candlestick_patterns
from QuantConnect import Resolution
from QuantConnect.Indicators import RollingWindow
from QuantConnect.Data.Consolidators import TradeBarConsolidator

class TechnicalIndicatorAlphaModel(AlphaModel):
    def __init__(self, indicator_strength=None):
        self.name="TechnicalIndicatorAlphaModel"
        super().__init__()
        self.symbolData = {}
        self.resolution = Resolution.Hour
        self.period = 20
        self.rebalancingPeriod = timedelta(hours=1)
        self.nextRebalance = datetime.min

        # Use provided indicator_strength object or create a new one
        self.indicator_strength = indicator_strength if indicator_strength is not None else IndicatorStrength()
        
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
            #Todo does reserve do what it should here
            prices = np.array([bar.Close for bar in reversed(list(symbolData.window))])
            highs = np.array([bar.High for bar in reversed(list(symbolData.window))])
            lows = np.array([bar.Low for bar in reversed(list(symbolData.window))])
            volumes = np.array([bar.Volume for bar in reversed(list(symbolData.window))])
            opens = np.array([bar.Open for bar in reversed(list(symbolData.window))])
            
            # Calculate indicators
            upper_trendline, lower_trendline = calculate_trendlines(highs, lows)
            support, resistance, historical_levels = calculate_support_resistance(prices)
            fib_levels = calculate_fibonacci_levels(prices)
            patterns = detect_candlestick_patterns(highs, lows, prices, opens)
            confidence = calculate_volume_confidence(volumes)
            
            # Generate insights based on technical indicators
            current_price = prices[-1]
            
            # Determine direction based on all indicators
            bullish_signals = 0.0
            bearish_signals = 0.0

            # Initialize lists to track which signals triggered
            triggered_bullish = []
            triggered_bearish = []

            # Market return data for indicator strength evaluation
            market_returns = []
            for i in range(1, min(30, len(prices))):
                market_returns.append((prices[-i] - prices[-i-1]) / prices[-i-1])

            # Evaluate signals for this symbol
            self.indicator_strength.evaluate_signals(algorithm.Time, symbol, current_price, market_returns)
            
            # Check trendlines
            trendline_indicator = "trendline"
            trendline_weight = self.indicator_strength.get_indicator_weight(symbol, trendline_indicator)

            if current_price > upper_trendline[-1]:
                bullish_signals += trendline_weight
                triggered_bullish.append("Above upper trendline")
                # Record this signal for future evaluation
                self.indicator_strength.record_signal(algorithm.Time, symbol, trendline_indicator, "bullish", current_price)
            elif current_price < lower_trendline[-1]:
                bearish_signals += trendline_weight
                triggered_bearish.append("Below lower trendline")
                # Record this signal for future evaluation
                self.indicator_strength.record_signal(algorithm.Time, symbol, trendline_indicator, "bearish", current_price)
                
            # Check trendline pullbacks and bounces
            trendline_threshold = 0.02  # 2% threshold
            price_history = prices[-5:]  # Look at last 5 periods
            
            # Bullish pullback to lower trendline
            pullback_indicator = "trendline_pullback"
            pullback_weight = self.indicator_strength.get_indicator_weight(symbol, pullback_indicator)

            if (abs(current_price - lower_trendline[-1]) / current_price < trendline_threshold and
                prices[-2] < lower_trendline[-2]):  # Price crossing back above trendline
                bullish_signals += pullback_weight
                triggered_bullish.append("Bullish pullback to lower trendline")
                self.indicator_strength.record_signal(algorithm.Time, symbol, pullback_indicator, "bullish", current_price)

                # Check for bounce
                bounce_indicator = "trendline_bounce"
                bounce_weight = self.indicator_strength.get_indicator_weight(symbol, bounce_indicator)

                if min(price_history) < lower_trendline[-1] and current_price > lower_trendline[-1]:
                    bullish_signals += bounce_weight  # Add extra signal for confirmed bounce
                    triggered_bullish.append("Confirmed bounce from lower trendline")
                    self.indicator_strength.record_signal(algorithm.Time, symbol, bounce_indicator, "bullish", current_price)

            # Bearish pullback to upper trendline    
            if (abs(current_price - upper_trendline[-1]) / current_price < trendline_threshold and
                prices[-2] > upper_trendline[-2]):  # Price crossing back below trendline
                bearish_signals += pullback_weight
                triggered_bearish.append("Bearish pullback to upper trendline")
                self.indicator_strength.record_signal(algorithm.Time, symbol, pullback_indicator, "bearish", current_price)

                # Check for bounce
                bounce_indicator = "trendline_bounce"
                bounce_weight = self.indicator_strength.get_indicator_weight(symbol, bounce_indicator)

                if max(price_history) > upper_trendline[-1] and current_price < upper_trendline[-1]:
                    bearish_signals += bounce_weight  # Add extra signal for confirmed bounce
                    triggered_bearish.append("Confirmed bounce from upper trendline")
                    self.indicator_strength.record_signal(algorithm.Time, symbol, bounce_indicator, "bearish", current_price)
                
            # Check support/resistance
            sr_indicator = "support_resistance"
            sr_weight = self.indicator_strength.get_indicator_weight(symbol, sr_indicator)

            if current_price < resistance and current_price > support:
                if abs(current_price - resistance) < abs(current_price - support):
                    bearish_signals += sr_weight
                    triggered_bearish.append("Closer to resistance than support")
                    self.indicator_strength.record_signal(algorithm.Time, symbol, sr_indicator, "bearish", current_price)
                else:
                    bullish_signals += sr_weight
                    triggered_bullish.append("Closer to support than resistance")
                    self.indicator_strength.record_signal(algorithm.Time, symbol, sr_indicator, "bullish", current_price)
                    
            # Check for support/resistance pullbacks and bounces
            short_ma = np.mean(prices[-5:])  # 5-period moving average
            long_ma = np.mean(prices[-20:])  # 20-period moving average
            
            # Bullish pullback: Price pulls back to support in uptrend
            sr_pullback_indicator = "sr_pullback"
            sr_pullback_weight = self.indicator_strength.get_indicator_weight(symbol, sr_pullback_indicator)

            if long_ma > short_ma and current_price > long_ma:
                if abs(current_price - support) / current_price < 0.02:  # Within 2% of support
                    bullish_signals += sr_pullback_weight
                    triggered_bullish.append("Bullish pullback to support in uptrend")
                    self.indicator_strength.record_signal(algorithm.Time, symbol, sr_pullback_indicator, "bullish", current_price)

                    # Check for bounce from support
                    sr_bounce_indicator = "sr_bounce"
                    sr_bounce_weight = self.indicator_strength.get_indicator_weight(symbol, sr_bounce_indicator)

                    if min(price_history) <= support and current_price > support:
                        bullish_signals += sr_bounce_weight
                        triggered_bullish.append("Confirmed bounce from support")
                        self.indicator_strength.record_signal(algorithm.Time, symbol, sr_bounce_indicator, "bullish", current_price)

            # Bearish pullback: Price pulls back to resistance in downtrend  
            if long_ma < short_ma and current_price < long_ma:
                if abs(current_price - resistance) / current_price < 0.02:  # Within 2% of resistance
                    bearish_signals += sr_pullback_weight
                    triggered_bearish.append("Bearish pullback to resistance in downtrend")
                    self.indicator_strength.record_signal(algorithm.Time, symbol, sr_pullback_indicator, "bearish", current_price)

                    # Check for bounce from resistance
                    sr_bounce_indicator = "sr_bounce"
                    sr_bounce_weight = self.indicator_strength.get_indicator_weight(symbol, sr_bounce_indicator)

                    if max(price_history) >= resistance and current_price < resistance:
                        bearish_signals += sr_bounce_weight
                        triggered_bearish.append("Confirmed bounce from resistance")
                        self.indicator_strength.record_signal(algorithm.Time, symbol, sr_bounce_indicator, "bearish", current_price)
                    
            # Check candlestick patterns
            # Process each pattern with its own weight

            # Helper function to process pattern signals
            def process_pattern(pattern_name, signal_type):
                pattern_weight = self.indicator_strength.get_indicator_weight(symbol, f"pattern_{pattern_name}")
                if signal_type == "bullish":
                    nonlocal bullish_signals
                    bullish_signals += pattern_weight
                    triggered_bullish.append(f"{pattern_name.replace('_', ' ').title()} pattern")
                else:  # bearish
                    nonlocal bearish_signals
                    bearish_signals += pattern_weight
                    triggered_bearish.append(f"{pattern_name.replace('_', ' ').title()} pattern")

                # Record signal for future evaluation
                self.indicator_strength.record_signal(
                    algorithm.Time, symbol, f"pattern_{pattern_name}", signal_type, current_price
                )

            # Basic candlestick patterns
            if patterns.get('bullish_engulfing'):
                process_pattern('bullish_engulfing', 'bullish')

            if patterns.get('bearish_engulfing'):
                process_pattern('bearish_engulfing', 'bearish')

            if patterns.get('bullish_harami') or patterns.get('bullish_harami_cross'):
                process_pattern('bullish_harami', 'bullish')

            if patterns.get('bearish_harami') or patterns.get('bearish_harami_cross'):
                process_pattern('bearish_harami', 'bearish')

            if patterns.get('piercing_line'):
                process_pattern('piercing_line', 'bullish')

            # Chart patterns
            if patterns.get('head_and_shoulders'):
                process_pattern('head_and_shoulders', 'bearish')

            if patterns.get('bull_flag'):
                process_pattern('bull_flag', 'bullish')

            if patterns.get('ascending_triangle'):
                process_pattern('ascending_triangle', 'bullish')

            if patterns.get('descending_triangle'):
                process_pattern('descending_triangle', 'bearish')

            if patterns.get('rising_wedge'):
                process_pattern('rising_wedge', 'bearish')  # Rising wedge is typically bearish

            if patterns.get('falling_wedge'):
                process_pattern('falling_wedge', 'bullish')  # Falling wedge is typically bullish

            if patterns.get('cup_and_handle'):
                process_pattern('cup_and_handle', 'bullish')

            if patterns.get('megaphone'):
                # Megaphone can be either bullish or bearish depending on context
                if current_price > prices[-2]:  # Using price action to determine direction
                    process_pattern('megaphone', 'bullish')
                else:
                    process_pattern('megaphone', 'bearish')

            if patterns.get('pennant'):
                # Pennant follows the prior trend
                if current_price > prices[-10]:  # Check if uptrend
                    process_pattern('pennant', 'bullish')
                else:
                    process_pattern('pennant', 'bearish')
            # Generate insight if signals are strong enough
            # Log signal strengths for debugging
            algorithm.Debug(f"{symbol}: Bullish={bullish_signals:.2f}, Bearish={bearish_signals:.2f}")

            # Calculate signal difference and required threshold
            signal_difference = abs(bullish_signals - bearish_signals)
            min_threshold = 1.0  # Minimum difference to generate a signal

            if bullish_signals > bearish_signals and signal_difference >= min_threshold:
                # Calculate magnitude based on price distances
                magnitude = min(abs(resistance - current_price) / current_price,
                             abs(upper_trendline[-1] - current_price) / current_price)

                # Scale confidence by signal strength difference
                adjusted_confidence = min(confidence * (signal_difference / 5.0), 1.0)

                # Create insight
                insights.append(Insight.Price(
                    symbol, timedelta(days=1), InsightDirection.Up,
                    magnitude, adjusted_confidence, sourceModel="TechnicalIndicatorAlphaModel"))

                # Log which signals triggered this insight
                algorithm.Debug(f"{symbol} BULLISH signals: {', '.join(triggered_bullish)}")

            elif bearish_signals > bullish_signals and signal_difference >= min_threshold:
                # Calculate magnitude based on price distances
                magnitude = min(abs(support - current_price) / current_price,
                             abs(lower_trendline[-1] - current_price) / current_price)

                # Scale confidence by signal strength difference
                adjusted_confidence = min(confidence * (signal_difference / 5.0), 1.0)

                # Create insight
                insights.append(Insight.Price(
                    symbol, timedelta(days=1), InsightDirection.Down,
                    magnitude, adjusted_confidence, sourceModel="TechnicalIndicatorAlphaModel"))

                # Log which signals triggered this insight
                algorithm.Debug(f"{symbol} BEARISH signals: {', '.join(triggered_bearish)}")
                    
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