import os
import time
import logging
from twisted.internet import reactor, defer
from neopets.shops import ShopWizardExhaustedError, ItemNotFoundInShopWizardError, \
    SomeoneBiddedHigherError
from neopets.common import Event

class SniperManager(object):
    def __init__(self, account, shops, config, auctions_dir):
        self._account = account
        self._logger = logging.getLogger(__name__)
        self._shops = shops
        self._handled_auctions = set()
        self._next_iteration = None
        self._running = False
        self._config = config
        self._auctions_dir = auctions_dir
        self._on_deal = Event()

    @property
    def on_deal(self):
        return self._on_deal

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
        for keyword in self._config.interesting_keywords:
            if keyword in auction.item.lower():
                self._logger.debug('%s is interesting because of keyword %s', auction.item, keyword)
                return True

        return False

    def _dump_auction(self, auction, info):
        with open(os.path.join(self._auctions_dir, str(auction.id)), 'w') as f:
            f.write('%s\n\n%s' % (auction, '\n'.join(repr(b) for b in info.bidders)))

    @defer.deferredGenerator
    def _snipe(self, auction, est_price):
        sniper_logger = logging.getLogger('%s(%s)' % (__name__, auction.id))

        sniper_logger.info('Sniping auction %s', auction.item)
        our_bid = 0
        while True:
            d = defer.waitForDeferred(self._shops.auction_house.get_auction_page(str(auction.link)))
            yield d
            info = d.getResult()

            if len(info.bidders) > 0:
                top_bidder = info.bidders[0].name
                me_top = top_bidder == self._account.username
                if not info.open:
                    sniper_logger.info('Auction closed. Won: %s', me_top)
                    self._dump_auction(auction, info)
                    if me_top:
                        self._on_deal.call(auction, info.bidders[0].bid)
                    return

                sniper_logger.debug('Auction refreshed. Top bidder: %s. Next bid: %d',
                                   info.bidders[0], info.next_bid)

                if me_top:
                    continue
            else:
                if not info.open:
                    sniper_logger.info('Auction closed without bidders')
                    return

                sniper_logger.debug('Auction refreshed. Top bidder: None. Next bid: %d',
                                   info.next_bid)

            next_bid = info.next_bid

            while True:
                required_np = next_bid - our_bid
                if self._account.neopoints < required_np:
                    sniper_logger.warning(
                        'We don\'t have enough neopoints for the next bid. Next bid: %d, Our bid: %d, Have: %d, Required: %d',
                        next_bid, our_bid, self._account.neopoints, required_np)
                    return

                if est_price - next_bid < self._config.profit_threshold:
                    sniper_logger.info('Next bit will be non-profitable. Quitting it')
                    return

                yield_ = (float(est_price) / next_bid - 1) * 100
                if yield_ < self._config.minimal_yield:
                    sniper_logger.info('Next bit will make the yield %.2f%%, which is below the minimal', yield_)
                    return

                sniper_logger.info('We\'re not at the top. Bidding for %d', next_bid)
                d = defer.waitForDeferred(self._shops.auction_house.bid(
                    auction.id, next_bid, info.refcode))
                yield d

                try:
                    d.getResult()
                except SomeoneBiddedHigherError as e:
                    self._logger.warning('Someone bidded higher. Current price: %d', e.current_price)
                    next_bid = e.current_price
                    continue

                our_bid = next_bid
                break

    @defer.deferredGenerator
    def _second_analysis(self, auction):
        if not self._running:
            self._logger.warning('Second analysis called while paused')
            yield False, 0
            return

        d = defer.waitForDeferred(self._shops.est_price_calc.calc(auction.item,
                                                                  self._config.item_samples))
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

        if deviation > self._config.item_price_max_deviation:
            self._logger.info('Estimated price for %s is too risky. Deviation: %.2f%%',
                              auction.item, deviation)
            yield False, 0
            return

        delta = est_price - auction.current_price
        yield_ = (float(est_price) / auction.current_price - 1) * 100

        if delta <= self._config.bargain_threshold:
            yield False, 0
            return

        if (yield_ > self._config.suspecious_yield_threshold) \
           and (not self._is_interesting_keyword(auction)):
            self._logger.info(
                'Found a suspecious bargain: %s (current price: %d, est price: %d, yield: %.2f%%, profit: %d)',
                auction.item, auction.current_price, est_price, yield_, delta)
            yield False, 0
            return

        if yield_ < self._config.minimal_yield:
            self._logger.info(
                'Found a bargain, but yield is too low: %s (current price: %d, est price: %d, yield: %.2f%%, profit: %d)',
                auction.item, auction.current_price, est_price, yield_, delta)
            yield False, 0
            return

        self._logger.info(
            'Found a bargain: %s (current price: %d, est price: %d, yield: %.2f%%, profit: %d)',
            auction.item, auction.current_price, est_price, yield_, delta)

        if self._account.neopoints < auction.current_price:
            self._logger.info(
                    'We don\'t have enough neopoints for the next bid. Next bid: %d, Have: %d',
                    auction.current_price, self._account.neopoints)
            yield False, 0
            return

        yield True, est_price

    def _first_analysis(self, auction):
        if self._is_interesting_keyword(auction):
            return True

        for keyword in self._config.bad_keywords:
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
            d = defer.waitForDeferred(self._second_analysis(auction))
            yield d
            should_continue, est_price = d.getResult()

            if not should_continue:
                return

            if not self._running:
                self._logger.warning('Skipping sniping of %s because we\'re not running', auction)
                return

            self.stop()
            before = time.time()
            d = defer.waitForDeferred(self._snipe(auction, est_price))
            yield d
            after = time.time()
            self._logger.info('Sniping done (%.2f seconds)', after - before)

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

        d = defer.waitForDeferred(self._shops.auction_house.get_main_page(0))
        yield d
        auctions = d.getResult()

        try:
            if self._account.neopoints < self._config.minimum_np_for_playing:
                self._logger.debug('Sniper iteration is skipped because we don\'t have NPs')
                return

            for auction in auctions[
                    self._config.minimal_auction_number: \
                    self._config.minimal_auction_number + self._config.auctions_to_analyze]:
                if auction.link in self._handled_auctions:
                    continue

                self._handled_auctions.add(auction.link)

                reactor.callLater(0, self._handle_auction, auction)

        finally:
            self._next_iteration = reactor.callLater(self._config.refresh_interval, self._iteration)
