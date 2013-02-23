import logging
from twisted.internet import reactor, defer
from neopets.shops import ShopWizardExhaustedError, ItemNotFoundInShopWizardError


class SniperManager(object):
    _INTERVAL = 60
    _AUCTIONS_TO_ANALYZE = 20
    _BARGAIN_THRSHOLD = 2000
    _PROFIT_THRESHOLD = 1500
    _INTERESTING_KEYWORDS = ('codestone', )
    _BAD_KEYWORDS = ('map', 'plushie', 'fading', 'weak')

    def __init__(self, account, shops):
        self._account = account
        self._logger = logging.getLogger(__name__)
        self._shops = shops
        self._handled_auctions = set()
        self._next_iteration = None
        self._running = False

    def run(self):
        reactor.callLater(0, self._iteration)
        self._running = True

    def stop(self):
        if self._next_iteration:
            if self._next_iteration.active():
                self._next_iteration.cancel()

        self._running = False

    def _handle_exaustion(self, time_to_resume):
        self._logger.warning('Shop wizard exhausted. Resuming in %d minutes', time_to_resume)
        if self._next_iteration:
            if self._next_iteration.active():
                self._next_iteration.reset(60 * time_to_resume + 2)

    def _is_interesting_keyword(self, auction):
        for keyword in self._INTERESTING_KEYWORDS:
            if keyword in auction.item.lower():
                self._logger.debug('%s is interesting because of keyword %s', auction.item, keyword)
                return True

        return False

    @defer.deferredGenerator
    def _snipe(self, auction, est_price):
        sniper_logger = logging.getLogger('%s(%s)' % (__name__, auction.id))

        sniper_logger.info('Sniping auction %s', auction.item)
        our_bid = 0
        while True:
            d = defer.waitForDeferred(self._shops.auction_house.get_auction_page(str(auction.link)))
            yield d
            info = d.getResult()

            top_bidder = info.bidders[0].name
            me_top = top_bidder == self._account.username
            if not info.open:
                sniper_logger.info('Auction closed. Won: %s', me_top)
                return

            sniper_logger.debug('Auction refreshed. Top bidder: %s. Next bid: %d',
                               info.bidders[0], info.next_bid)

            if me_top:
                continue

            required_np = info.next_bid - our_bid
            if self._account.neopoints < required_np:
                sniper_logger.warning(
                    'We don\'t have enough neopoints for the next bid. Next bid: %d, Our bid: %d, Have: %d, Required: %d',
                    info.next_bid, our_bid, self._account.neopoints, required_np)
                return

            if est_price - info.next_bid < self._PROFIT_THRESHOLD:
                sniper_logger.info('Next bit will be non-profitable. Quitting it')
                return

            sniper_logger.info('We\'re not at the top. Bidding for %d', info.next_bid)
            d = defer.waitForDeferred(self._shops.auction_house.bid(
                auction.id, info.next_bid, info.refcode))
            yield d
            d.getResult()

            our_bid = info.next_bid

    @defer.deferredGenerator
    def _second_analyze(self, auction):
        if not self._running:
            self._logger.warning('Second analysis called while paused')
            yield False, 0
            return

        d = defer.waitForDeferred(self._shops.est_price_calc.calc(auction.item))
        yield d

        try:
            est_price, deviation = d.getResult()

        except ShopWizardExhaustedError as e:
            self._handle_exaustion(e.resume_time)
            yield False, 0
            return

        except ItemNotFoundInShopWizardError:
            self._logger.error('%s not found in shop wizard', auction.item)
            yield False, 0
            return

        if deviation > 33:
            self._logger.info('Estimated price for %s is too risky. Deviation: %.2f%%',
                              auction.item, deviation)
            yield False, 0
            return

        delta = est_price - auction.current_price
        yield_ = (float(est_price) / auction.current_price - 1) * 100

        if delta <= self._BARGAIN_THRSHOLD:
            yield False, 0
            return

        if (yield_ > 100.0) and (not self._is_interesting_keyword(auction)):
            self._logger.info(
                'Found a suspecious bargain: %s (current price: %d, est price: %d, yield: %.2f%%, profit: %d)',
                auction.item, auction.current_price, est_price, yield_, delta)
            yield False, 0
            return

        self._logger.info(
            'Found a bargain: %s (current price: %d, est price: %d, yield: %.2f%%, profit: %d)',
            auction.item, auction.current_price, est_price, yield_, delta)

        yield True, est_price

    def _first_analysis(self, auction):
        if self._is_interesting_keyword(auction):
            return True

        for keyword in self._BAD_KEYWORDS:
            if keyword in auction.item.lower():
                self._logger.debug('%s is skipped because of keyword %s', auction.item, keyword)
                return False

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
            should_continue, est_price = d.getResult()

            if not should_continue:
                return

            if not self._running:
                self._logger.warning('Skipping sniping of %s because we\'re not running', auction)
                return

            self.stop()
            d = defer.waitForDeferred(self._snipe(auction, est_price))
            yield d
            self._logger.info('Sniping done')

            try:
                d.getResult()
            finally:
                self.run()

    @defer.deferredGenerator
    def _iteration(self):
        if not self._running:
            self._logger.warning('Sniper iteration called while paused')
            return

        self._logger.debug('Sniper iteration')

        d = defer.waitForDeferred(self._shops.auction_house.get_main_page(1))
        yield d
        auctions = d.getResult()

        for auction in auctions[:self._AUCTIONS_TO_ANALYZE]:
            if auction.link in self._handled_auctions:
                continue

            self._handled_auctions.add(auction.link)

            reactor.callLater(0, self._handle_auction, auction)

        self._next_iteration = reactor.callLater(self._INTERVAL, self._iteration)
