import logging
from twisted.internet import task, reactor
from twisted.internet.defer import Deferred
from neopets.restocking.restocker import Restocker
from neopets.restocking.pricecalc import EstPriceCalculator

class Manager(object):
    def __init__(self, account, db, shops, refresh_interval, shops_to_restock):
        self._logger = logging.getLogger(__name__)
        self._refresh_interval = refresh_interval
        self._work = False

        new_items_deferred = Deferred()
        new_items_deferred.addCallback(self._on_new_items)

        self._logger.info('Restockers: %s', ', '.join(shops_to_restock))
        self._restockers = [
            Restocker(db, shops.get_neopian(shop), account,
                      new_items_deferred)
            for shop in shops_to_restock]

        self._restocker_index = 0

        self._price_calc = EstPriceCalculator(account, db,
                                              shops)

    def start(self):
        self._work = True
        self._next(None)
        self._price_calc.recalc()

    def _next(self, _):
        if not self._work:
            self._logger.info('Restocker manager is stopping')
            return

        restocker = self._restockers[self._restocker_index]
        d = restocker.refresh()
        d.addCallback(self._on_successful_refresh)
        d.addErrback(self._on_error_refresh)

    def _on_successful_refresh(self, _):
        self._logger.debug('Restocker finished successfully')
        self._restocker_index += 1
        if self._restocker_index >= len(self._restockers):
            self._restocker_index = 0

        task.deferLater(reactor, self._refresh_interval, self._next,
                        None)

    def _on_error_refresh(self, result):
        self._logger.error('Error in restocker: %s', result)
        self._work = False

    def _on_new_items(self, _):
        self._logger.debug('A restocker recorded new items. Recalcing prices')
        self._price_calc.recalc()
