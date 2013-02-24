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

        offers, section = d.getResult()

        n_offers = len(offers)
        if n_offers == 0:
            self._logger.warning('No results for %s', item)
            yield (0, section)
            return

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

        yield (avg, section)

    @defer.deferredGenerator
    def calc(self, item, samples=3):
        results = []
        recorded_letters = set()

        while True:
            d = defer.waitForDeferred(self._calc_sample(item))
            yield d
            price, letters = d.getResult()

            if letters in recorded_letters:
                self._logger.debug('Letters %s for item %s already recorded', letters, item)
                continue

            recorded_letters.add(letters)
            results.append((price, letters))
            if len(results) >= samples:
                break

        price_list = [price for price, _ in results]
        deviation = (float(max(price_list)) / float(min(price_list)) - 1) * 100
        avg = sum(price_list) / samples

        self._logger.debug('Results for %s: %s. Avg: %d. Deviation: %.2f%%',
                           item, results, avg, deviation)

        yield avg, deviation
