from datetime import timedelta
from QuantConnect.Algorithm.Framework.Portfolio import PortfolioConstructionModel as PCM
from QuantConnect.Algorithm.Framework.Portfolio import PortfolioTarget
from QuantConnect.Algorithm.Framework.Alphas import InsightDirection

class PortfolioConstructionModel(PCM):
    """
    Portfolio construction model that uses indicator strength to help determine position sizing
    """

    def __init__(self, rebalance_period=timedelta(days=1), max_turnover=0.1, max_weight=0.25):
        """
        Initialize the portfolio construction model

        Parameters:
        rebalance_period (timedelta): Period between portfolio rebalances
        max_turnover (float): Maximum turnover per rebalance (0.1 = 10%)
        max_weight (float): Maximum weight for any single position
        """
        super().__init__()
        self.rebalance_period = rebalance_period
        self.max_turnover = max_turnover
        self.max_weight = max_weight
        self.next_rebalance = None
        self.previous_targets = {}

    def CreateTargets(self, algorithm, insights):
        """Create portfolio targets based on insights"""
        # Skip if no insights or not time to rebalance
        if not insights or (self.next_rebalance is not None and algorithm.Time < self.next_rebalance):
            return []

        self.next_rebalance = algorithm.Time + self.rebalance_period

        # Get current portfolio holdings
        current_holdings = {}
        for kvp in algorithm.Portfolio:
            if kvp.Value.Invested:
                current_holdings[kvp.Key] = kvp.Value.HoldingsValue / algorithm.Portfolio.TotalPortfolioValue

        # Group insights by symbol and direction
        symbol_insights = {}
        for insight in insights:
            symbol_insights.setdefault(insight.Symbol, [])
            symbol_insights[insight.Symbol].append(insight)

        # Create new targets considering alpha strength
        new_targets = {}
        total_conviction = 0

        # First pass - calculate raw conviction scores
        for symbol, symbol_insights_list in symbol_insights.items():
            # Calculate net conviction
            net_conviction = 0
            for insight in symbol_insights_list:
                # Scale by confidence and magnitude
                direction_multiplier = 1 if insight.Direction == InsightDirection.Up else -1
                net_conviction += direction_multiplier * insight.Confidence * insight.Magnitude

            # Store absolute conviction for weighting
            if net_conviction != 0:
                # Store with direction information preserved
                new_targets[symbol] = net_conviction
                total_conviction += abs(net_conviction)

        # Second pass - normalize targets
        portfolio_targets = []
        if total_conviction > 0:
            for symbol, conviction in new_targets.items():
                # Calculate target percentage (preserve direction with sign)
                direction = 1 if conviction > 0 else -1
                weight = direction * min(self.max_weight, abs(conviction) / total_conviction)

                # Create portfolio target
                portfolio_targets.append(PortfolioTarget(symbol, weight))

        # Apply turnover constraint
        constrained_targets = self.apply_turnover_constraint(algorithm, current_holdings, portfolio_targets)

        # Update previous targets
        self.previous_targets = {target.Symbol: target.Quantity for target in constrained_targets}

        return constrained_targets

    def apply_turnover_constraint(self, algorithm, current_holdings, targets):
        """Apply turnover constraint to limit portfolio changes"""
        # Calculate turnover for proposed targets
        total_turnover = 0
        for target in targets:
            current_weight = current_holdings.get(target.Symbol, 0)
            target_weight = target.Quantity
            turnover = abs(target_weight - current_weight)
            total_turnover += turnover

        # If turnover is acceptable, return original targets
        if total_turnover <= self.max_turnover:
            return targets

        # Otherwise, scale back targets to meet turnover constraint
        scaling_factor = self.max_turnover / total_turnover
        constrained_targets = []

        for target in targets:
            current_weight = current_holdings.get(target.Symbol, 0)
            target_weight = target.Quantity

            # Scale the weight change
            weight_change = (target_weight - current_weight) * scaling_factor
            new_weight = current_weight + weight_change

            # Only create targets that result in actual changes
            if abs(new_weight - current_weight) > 0.001:
                constrained_targets.append(PortfolioTarget(target.Symbol, new_weight))

        return constrained_targets
