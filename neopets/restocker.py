import logging
from contextlib import closing
from twisted.internet import task, reactor
from sqlalchemy.sql import select

class Restocker(object):
    def __init__(self, db, shop, account, refresh_interval, new_items_deferred):
        self._logger = logging.getLogger(
            '%s(%s)' % (__name__, shop.name))
        self._account = account
        self._work = False
        self._shop = shop
        self._items = None
        self._db = db
        self._refresh_interval = refresh_interval
        self._new_items_deferred = new_items_deferred

    def start(self):
        self._logger.info('Started')
        self._items = dict()
        self._work = True
        d = task.deferLater(reactor, 0, self._refresh,
                            None)
        d.addCallback(self._on_refreshed)
        d.addErrback(self._on_error)
        return d

    def _on_refreshed(self, _):
        self._logger.debug('Refresh finished successfully')
        if not self._work:
            self._logger.info('Stopped')
            return

        d = task.deferLater(reactor, self._refresh_interval, self._refresh,
                            None)
        d.addCallback(self._on_refreshed)
        d.addErrback(self._on_error)
        return d

    def _on_error(self, result):
        self._logger.error('Error: %s', result)

    def _refresh(self, _):
        self._logger.debug('Refreshing')
        d = self._shop.get_items()
        d.addCallback(self._on_items)
        return d

    def _record_item(self, item):
        items = self._db.tables.items
        with self._db.engine.connect() as conn:
            query = select([items.c.shop_price],
                           items.c.item_name == item.name)

            with closing(conn.execute(query)) as result:
                r = result.fetchone()

            if not r:
                self._logger.info(
                    'Recording \'%s\' to the database (Shop price: %d)',
                    item.name, item.price)

                query = items.insert().values(item_name=item.name,
                                              shop_price=item.price,
                                              shop_name=self._shop.name)

                conn.execute(query)
                return True

            if r.shop_price != item.price:
                self._logger.info('Price of %s changed from %d to %d',
                                  item.name, r.shop_price, item.price)
                query = items.update().where(
                    items.c.item_name == item.name).values(
                        shop_price=item.price)
                conn.execute(query)

        return False

    def _on_items(self, items):
        item_names = set()
        new_items = False

        for item in items:
            item_names.add(item.name)

            if item.name not in self._items:
                self._items[item.name] = item
                self._logger.debug('New item: %r', item)
            else:
                if self._items[item.name].in_stock != item.in_stock:
                    self._logger.debug('%s: %d -> %d', item.name,
                                      self._items[item.name].in_stock,
                                      item.in_stock)
                    self._items[item.name] = item


            if self._record_item(item):
                new_items = True

        deleted_items = frozenset(self._items.iterkeys()) - item_names
        for d_item in deleted_items:
            self._logger.debug('Deleted item %s', d_item)
            del self._items[d_item]

        if new_items:
            self._logger.debug('New items recorded')
            self._new_items_deferred.callback(None)
