import logging
from twisted.internet import reactor, defer


class SniperManager(object):
    _INTERVAL = 60
    _AUCTIONS_TO_ANALYZE = 5
    _BARGAIN_THRSHOLD = 1500

    def __init__(self, account, shops):
        self._account = account
        self._logger = logging.getLogger(__name__)
        self._shops = shops
        self._handled_auctions = set()

    def run(self):
        reactor.callLater(0, self._iteration)

    @defer.deferredGenerator
    def _handle_auction(self, auction):
        self._logger.debug('Analyzing %s', auction)

        d = defer.waitForDeferred(self._shops.est_price_calc.calc(auction.item, 3))
        yield d
        est_price = d.getResult()

        delta = est_price - auction.current_price
        yield_ = (float(est_price) / auction.current_price - 1) * 100
        if delta > self._BARGAIN_THRSHOLD:
            self._logger.info('Found a bargain: %s (current price: %d, est price: %d)',
                              auction.item, auction.current_price, est_price)

        self._logger.debug('%s: current price: %d, est price: %d (%.2f%%)',
                           auction.item, auction.current_price, est_price, yield_)

        yield True

    @defer.deferredGenerator
    def _iteration(self):
        d = defer.waitForDeferred(self._shops.auction_house.get_main_page())
        yield d
        auctions = d.getResult()

        for auction in auctions[-self._AUCTIONS_TO_ANALYZE:]:
            if auction in self._handled_auctions:
                self._logger.debug('already handling %s', auction)
                continue

            self._handled_auctions.add(auction)
            if auction.current_price >= 100000:
                self._logger.debug('%s price (%d) is too high to sell in stores',
                                   auction.item, auction.current_price)
                continue

            reactor.callLater(0, self._handle_auction, auction)

        reactor.callLater(self._INTERVAL, self._iteration)

        yield True
