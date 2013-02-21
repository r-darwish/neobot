import logging
from twisted.internet import defer


class EstPriceCalculator(object):
    _MAX_ENTRIES = 3
    _MINIMUM_ENTRIES = 5

    def __init__(self, shops):
        self._shops = shops
        self._logger = logging.getLogger(__name__)

    @defer.deferredGenerator
    def _calc_sample(self, item):
        d = defer.waitForDeferred(self._shops.wizard.get_offers(item))
        yield d

        offers = d.getResult()
        n_offers = len(offers)
        if n_offers == 0:
            self._logger.warning('No results for %s', item)
            yield 0

        else:
            if n_offers < self._MINIMUM_ENTRIES:
                self._logger.warning('%d offers for %s, which is below the minimum '
                                     'offers for a price', n_offers, item)

            offers_to_calc = min(self._MAX_ENTRIES, len(offers))
            avg = 0
            weights = 0
            for i in xrange(offers_to_calc):
                offer = offers[i]
                avg += offer.price * offer.stock
                weights += offer.stock

            avg /= weights

            yield avg

    @defer.deferredGenerator
    def calc(self, item, samples=3):
        results = []
        for _ in xrange(samples):
            results.append(self._calc_sample(item))

        d = defer.waitForDeferred(defer.DeferredList(results, consumeErrors=True))
        yield d
        results = d.getResult()

        self._logger.debug('Results for %s: %s', item, [r for _, r in results])

        avg = 0
        for succeeded, result in results:
            if not succeeded:
                raise result

            avg += result

        avg /= samples

        yield avg
