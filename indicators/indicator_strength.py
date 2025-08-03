from datetime import timedelta
import numpy as np
from collections import defaultdict

class IndicatorStrength:
    def __init__(self, lookback_period=30*24):  # 30 days * 24 hours for hourly data
        self.lookback_period = lookback_period
        # Structure: {symbol: {indicator_name: IndicatorStats}}
        self.asset_indicators = defaultdict(lambda: {})
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
            
    def record_signal(self, timestamp, symbol, indicator_name, direction, price):
        """Record a new signal from an indicator for a specific asset

        Parameters:
        timestamp (datetime): The time when the signal was generated
        symbol (Symbol): The asset symbol
        indicator_name (str): Name of the indicator generating the signal
        direction (str): 'bullish' or 'bearish'
        price (float): Current price when signal was generated
        """
        # Initialize indicator stats if not exists for this asset and indicator
        if indicator_name not in self.asset_indicators[symbol]:
            self.asset_indicators[symbol][indicator_name] = self.IndicatorStats()

        self.signals.append({
            'timestamp': timestamp,
            'symbol': symbol,
            'indicator': indicator_name,
            'direction': direction,
            'entry_price': price,
            'evaluated': False
        })

        self.asset_indicators[symbol][indicator_name].total_signals += 1
        
        # Remove signals older than lookback period
        cutoff_time = timestamp - timedelta(hours=self.lookback_period)
        self.signals = [s for s in self.signals if s['timestamp'] > cutoff_time]
        
    def evaluate_signals(self, current_time, symbol, current_price, market_return):
        """Evaluate previous signals and update indicator statistics

        Parameters:
        current_time (datetime): Current time for evaluation
        symbol (Symbol): The asset symbol to evaluate
        current_price (float): Current price of the asset
        market_return (array): Array of market returns for calculating alpha/beta
        """
        # Filter signals for this symbol
        symbol_signals = [s for s in self.signals if s['symbol'] == symbol and not s['evaluated']]

        for signal in symbol_signals:
            # Only evaluate signals that are at least 1 period old
            if (current_time - signal['timestamp']).total_seconds() < 3600:
                continue

            signal['evaluated'] = True
            indicator = self.asset_indicators[symbol][signal['indicator']]

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
            if len(indicator.signal_returns) > 1 and len(market_return) >= len(indicator.signal_returns):
                returns = np.array(indicator.signal_returns)
                market_returns = np.array(market_return[-len(returns):])

                try:
                    # Beta = covariance(signal, market) / variance(market)
                    cov_matrix = np.cov(returns, market_returns)
                    if cov_matrix.shape == (2, 2) and np.var(market_returns) != 0:
                        beta = cov_matrix[0,1] / np.var(market_returns)

                        # Alpha = average signal return - beta * average market return
                        alpha = np.mean(returns) - (beta * np.mean(market_returns))

                        indicator.alpha = alpha
                        indicator.beta = beta
                except Exception as e:
                    # Handle numerical issues gracefully
                    pass
                
    def get_indicator_metrics(self, symbol, indicator_name):
        """Get current statistics for an indicator for a specific asset

        Parameters:
        symbol (Symbol): The asset symbol
        indicator_name (str): The name of the indicator

        Returns:
        dict: Dictionary containing indicator metrics, or None if not found
        """
        if symbol not in self.asset_indicators or indicator_name not in self.asset_indicators[symbol]:
            return None

        ind = self.asset_indicators[symbol][indicator_name]
        accuracy = ind.true_positives / ind.total_signals if ind.total_signals > 0 else 0

        return {
            'accuracy': accuracy,
            'total_signals': ind.total_signals,
            'cumulative_return': ind.cumulative_return,
            'alpha': ind.alpha,
            'beta': ind.beta
        }

    def get_indicator_weight(self, symbol, indicator_name, min_weight=0.2, default_weight=0.5):
        """Calculate a weight for an indicator based on its historical performance

        Parameters:
        symbol (Symbol): The asset symbol
        indicator_name (str): The name of the indicator
        min_weight (float): Minimum weight to assign (default: 0.2)
        default_weight (float): Default weight when no history (default: 0.5)

        Returns:
        float: Weight between min_weight and 1.0
        """
        metrics = self.get_indicator_metrics(symbol, indicator_name)

        if metrics is None or metrics['total_signals'] < 5:
            return default_weight  # Not enough history to judge

        # Weight based on accuracy and adjusted by alpha
        weight = metrics['accuracy']

        # Adjust by alpha if available (positive alpha increases weight)
        if metrics['alpha'] != 0:
            alpha_adjustment = min(max(1 + metrics['alpha'], 0.5), 1.5)  # Limit between 0.5x and 1.5x
            weight *= alpha_adjustment

        # Ensure weight is between min_weight and 1.0
        return max(min_weight, min(weight, 1.0))