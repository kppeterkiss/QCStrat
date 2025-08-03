# region imports
from AlgorithmImports import *
# endregion
class LargeCapCryptoUniverseAlgorithm(QCAlgorithm):
    def initialize(self):
        self.set_start_date(2020, 1, 1)
        self.set_end_date(2021, 1, 1)
        # Set the account currency. USD is already the default value. Change it here if you want.
        self.set_account_currency("USD")
        # Get the pairs that our brokerage supports and have a quote currency that
        # matches your account currency. We need this list in the universe selection function.
        self._market = Market.COINBASE
        self._market_pairs = [
            x.key.symbol
            for x in self.symbol_properties_database.get_symbol_properties_list(self._market)
            if x.value.quote_currency == self.account_currency
        ]
        # Add a universe of Cryptocurrencies.
        self._universe = self.add_universe(CoinGeckoUniverse, self._select_assets)
        # Add a Sheduled Event to rebalance the portfolio.
        self.schedule.on(self.date_rules.every_day(), self.time_rules.at(12, 0), self._rebalance)

    def _select_assets(self, data: list[CoinGeckoUniverse]) -> list[Symbol]:
        # Select the coins that our brokerage supports and have a quote currency that matches
        # our account currency.
        tradable_coins = [d for d in data if d.coin + self.account_currency in self._market_pairs]
        # Select the largest coins and create their Symbol objects.
        return [
            c.create_symbol(self._market, self.account_currency)
            for c in sorted(tradable_coins, key=lambda x: x.market_cap)[-10:]
        ]

    def _rebalance(self):
        if not self._universe.selected:
            return
        symbols = [symbol for symbol in self._universe.selected if self.securities[symbol].price]
        # Liquidate coins that are no longer in the universe.
        targets = [PortfolioTarget(symbol, 0) for symbol, holding in self.portfolio.items() if
                   holding.invested and symbol not in symbols]
        # Form an equal weighted portfolio of the coins in the universe.
        targets += [PortfolioTarget(symbol, 0.5 / len(symbols)) for symbol in symbols]
        # Place orders to rebalance the portfolio.
        self.set_holdings(targets)
