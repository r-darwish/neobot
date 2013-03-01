import logging
from twisted.internet import defer


class UnknownStrategyError(Exception):
    def __init__(self, strategy):
        super(UnknownStrategyError, self).__init__(
            'Unknown strategy %s. Available strategies: %s' % (strategy, AutoPricer.STRATEGIES))


class AutoPricer(object):
    STRATEGIES = ('book', 'estimated_price')

    def __init__(self, account, shops, config):
        self._logger = logging.getLogger(__name__)
        self._account = account
        self._shops = shops
        self._config = config

        if self._config.strategy not in self.STRATEGIES:
            raise UnknownStrategyError(self._config.strategy)

    @defer.deferredGenerator
    def _price(self, item):
        self._logger.info('Pricing %s', item)

        d = defer.waitForDeferred(self._shops.est_price_calc.calc(item))
        yield d
        est_price, _ = d.getResult()
        self._logger.debug('EST Price is %d', est_price)

        if self._config.strategy == 'estimated_price':
            yield est_price
            return

        d = defer.waitForDeferred(self._shops.wizard.get_offers_from_section(
            item, self._shops.wizard.my_section))
        yield d
        my_section_offers = d.getResult()

        best_offer = my_section_offers[0]
        self._logger.debug('Best offer in my section: %d / %d NP', best_offer.stock, best_offer.price)
        book_suggested_price = best_offer.price - 10

        yield min(est_price, book_suggested_price)

    @defer.deferredGenerator
    def run(self):
        d = defer.waitForDeferred(self._shops.my_shop.get_main_page())
        yield d
        items = d.getResult()

        for item in (x for x in items if x.price == 0):
            d = defer.waitForDeferred(self._price(item.name))
            yield d
            price = d.getResult()
            self._logger.info('Price for %s should be %d', item.name, price)
