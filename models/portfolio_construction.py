from QuantConnect.Algorithm.Framework.Portfolio import PortfolioTarget
from QuantConnect.Algorithm.Framework.Alphas import InsightDirection

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