from QuantConnect.Algorithm import QCAlgorithm
from QuantConnect.Data.Market import TradeBar
from QuantConnect.Resolution import Resolution

from .models.technical_alpha import TechnicalIndicatorAlphaModel
from .models.portfolio_construction import PortfolioConstructionModel

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