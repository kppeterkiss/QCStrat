from datetime import timedelta
import numpy as np

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