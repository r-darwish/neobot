import logging
from twisted.internet import reactor, defer
from neopets.shops import ShopWizardExhaustedError


class SniperManager(object):
    _INTERVAL = 60
    _AUCTIONS_TO_ANALYZE = 5
    _BARGAIN_THRSHOLD = 1500

    def __init__(self, account, shops):
        self._account = account
        self._logger = logging.getLogger(__name__)
        self._shops = shops
        self._handled_auctions = set()
        self._next_iteration = None

    def run(self):
        reactor.callLater(0, self._iteration)

    def _handle_exaustion(self, time_to_resume):
        self._logger.warning('Shop wizard exhausted. Resuming in %d minutes', time_to_resume)
        if self._next_iteration:
            if self._next_iteration.active():
                self._next_iteration.reset(60 * time_to_resume + 2)

    @defer.deferredGenerator
    def _second_analyze(self, auction):
        d = defer.waitForDeferred(self._shops.est_price_calc.calc(auction.item, 5))
        yield d

        try:
            est_price = d.getResult()
        except ShopWizardExhaustedError as e:
            self._handle_exaustion(e.resume_time)
        else:
            delta = est_price - auction.current_price
            yield_ = (float(est_price) / auction.current_price - 1) * 100
            self._logger.debug('%s: current price: %d, est price: %d (%d - %.2f%%)',
                               auction.item, auction.current_price, est_price, delta, yield_)

            if delta > self._BARGAIN_THRSHOLD:
                if yield_ > 100.0:
                    self._logger.info('Found a suspecious bargain: %s (current price: %d, est price: %d)',
                                      auction.item, auction.current_price, est_price)
                    yield False, 0
                else:
                    self._logger.info('Found a bargain: %s (current price: %d, est price: %d)',
                                      auction.item, auction.current_price, est_price)

                    yield True, est_price

            else:
                yield False, 0

    def _first_analysis(self, auction):
        if not auction.last_bidder:
            self._logger.debug('No last bidder for %s', auction.item)
            return False

        if auction.current_price >= 100000:
            self._logger.debug('%s price (%d) is too high to sell in stores',
                               auction.item, auction.current_price)
            return False

        if auction.current_price < 1000:
            self._logger.debug('Current price of %s is %d. Probably not interesting',
                               auction.item, auction.current_price)
            return False

        return True

    @defer.deferredGenerator
    def _handle_auction(self, auction):
        if self._first_analysis(auction):
            d = defer.waitForDeferred(self._second_analyze(auction))
            yield d
            should_continue, _ = d.getResult()

            if should_continue:
                self._logger.info('%s should be sniped', auction)

    @defer.deferredGenerator
    def _iteration(self):
        self._logger.debug('Sniper iteration')

        d = defer.waitForDeferred(self._shops.auction_house.get_main_page())
        yield d
        auctions = d.getResult()

        for auction in auctions[-self._AUCTIONS_TO_ANALYZE:]:
            if auction.link in self._handled_auctions:
                self._logger.debug('already handling %s', auction)
                continue

            self._handled_auctions.add(auction.link)

            reactor.callLater(0, self._handle_auction, auction)

        self._next_iteration = reactor.callLater(self._INTERVAL, self._iteration)

        yield True
