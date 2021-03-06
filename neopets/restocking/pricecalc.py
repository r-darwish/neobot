import logging
import datetime
from contextlib import closing
from sqlalchemy.sql import select
from twisted.internet import defer


class EstPriceCalculator(object):
    _MAX_ENTRIES = 3
    _MINIMUM_ENTRIES = 10

    def __init__(self, account, db, shops):
        self._account = account
        self._db = db
        self._logger = logging.getLogger(__name__)
        self._items_to_calc = set()
        self._shops = shops

    @defer.deferredGenerator
    def recalc(self):
        items = self._db.tables.items
        items_to_recalc = set()
        with self._db.engine.connect() as conn:
            query = select([items.c.item_name]).where(items.c.est_price == None)
            with closing(conn.execute(query)) as result:
                for item in result:
                    self._logger.debug('%s has no est price', item.item_name)
                    items_to_recalc.add(item.item_name)

        for item in items_to_recalc:
            yield defer.waitForDeferred(self._calc_price(item))

        self._logger.debug('No more items to recalc')

    @defer.deferredGenerator
    def _calc_price(self, item):
        self._logger.debug('Fetching results for %s', item)
        d = defer.waitForDeferred(self._shops.wizard.get_offers(item))
        yield d
        self._logger.debug('Parsing results for %s', item)

        offers = d.getResult()
        n_offers = len(offers)
        if n_offers < self._MINIMUM_ENTRIES:
            self._logger.warning('%d offers for %s, which is below the minimum '
                                 'offers for a price', n_offers, item.name)

        offers_to_calc = min(self._MAX_ENTRIES, len(offers))
        avg = 0
        weights = 0
        for i in xrange(offers_to_calc):
            offer = offers[i]
            avg += offer.price * offer.stock
            weights += offer.stock

        avg /= weights

        self._logger.debug('%s: Est price is %d', item, avg)

        with self._db.engine.connect() as conn:
            items = self._db.tables.items
            query = items.update().where(items.c.item_name == item).values(
                est_price=avg, est_price_date=datetime.datetime.now())
            conn.execute(query)
