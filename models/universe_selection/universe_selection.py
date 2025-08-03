from AlgorithmImports import *
import numpy as np
from datetime import timedelta

class VolumeVolatilityUniverseSelectionModel:
    """
    Universe selection model that selects top cryptocurrency pairs by volume and volatility.
    First, it filters the top 50 trading pairs with USDC by trading volume.
    Then, it selects the top 10 most volatile pairs among those.
    """

    def __init__(self, lookback_days=30):
        """
        Initialize the universe selection model

        Parameters:
        lookback_days (int): Number of days to look back for volume and volatility calculations
        """
        self.lookback_days = lookback_days
        self.usdc_pair_filter = "USDC"
        self.top_by_volume = 50
        self.top_by_volatility = 10
        self.next_refresh_time = None
        self.refresh_period = timedelta(days=1)  # Refresh universe daily

    def filter(self, fundamental: list[Fundamental]):
    #def filter_coarse(self, algorithm, coarse):
        """
        Filters the universe to find the top cryptocurrency pairs by volume and volatility

        Parameters:
        algorithm (QCAlgorithm): The algorithm instance
        coarse (list): List of CoarseFundamental objects

        Returns:
        list: List of Symbol objects representing the selected universe
        """
        # Check if it's time to refresh the universe
        if self.next_refresh_time is not None and algorithm.Time < self.next_refresh_time:
            return algorithm.Universe.Unchanged

        self.next_refresh_time = algorithm.Time + self.refresh_period

        # Filter for USDC pairs
        usdc_pairs = [cf for cf in coarse if self.usdc_pair_filter in cf.Symbol.Value]

        if len(usdc_pairs) == 0:
            algorithm.Debug("No USDC pairs found")
            return []

        # Sort by dollar volume (descending) and take top 50
        by_volume = sorted(usdc_pairs, key=lambda x: x.DollarVolume, reverse=True)[:self.top_by_volume]

        if len(by_volume) == 0:
            return []

        # Calculate volatility for each pair
        volatility_data = []
        lookback = timedelta(days=self.lookback_days)
        history_start = algorithm.Time - lookback

        for coin in by_volume:
            try:
                # Get historical data for volatility calculation
                history = algorithm.History([coin.Symbol], lookback, Resolution.Daily)

                if history.empty or len(history) < 7:  # Require at least a week of data
                    continue

                # Calculate daily returns
                close_prices = history['close']
                daily_returns = close_prices.pct_change().dropna()

                # Calculate volatility (standard deviation of returns)
                volatility = daily_returns.std()

                volatility_data.append((coin.Symbol, volatility))
            except Exception as e:
                algorithm.Debug(f"Error calculating volatility for {coin.Symbol}: {e}")

        # Sort by volatility (descending) and take top 10
        volatility_data.sort(key=lambda x: x[1], reverse=True)
        selected = [pair[0] for pair in volatility_data[:self.top_by_volatility]]

        algorithm.Debug(f"Selected {len(selected)} pairs based on volume and volatility")
        return selected
