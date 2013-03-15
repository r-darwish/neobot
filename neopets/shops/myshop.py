import logging
import re
from twisted.internet import defer
from neopets.common import PageParseError
from collections import namedtuple


MyShopItem = namedtuple('MyShopItem', ('id', 'index', 'name', 'stock', 'price'))


class MyShop(object):
    _OBJ_ID_RE = re.compile(r'obj_id_(\d+)')

    def __init__(self, account):
        self._logger = logging.getLogger(__name__)
        self._account = account

    @defer.deferredGenerator
    def get_main_page(self):
        d = defer.waitForDeferred(self._account.get('market_your.phtml'))
        yield d
        page = d.getResult()

        name_col = page.find('b', text='Name')
        if not name_col:
            if page.find('b', text='There are no items in your shop!'):
                self._logger.info('No items in the shop')
                yield []
                return

            raise PageParseError(page)

        items = []
        items_input = page.findAll('input', attrs={ 'name' : self._OBJ_ID_RE })
        for item_input in items_input:
            tr = item_input.previousSibling.findParent('tr')
            index = int(self._OBJ_ID_RE.search(item_input['name']).group(1))
            tds = tr.findAll('td')
            items.append(MyShopItem(
                tr.find('input', attrs={'name' : 'obj_id_%d' % (index, ) })['value'],
                index,
                tds[0].find('b').text,
                int(tds[2].find('b').text),
                int(tr.find('input', attrs={'name' : 'oldcost_%d' % (index, ) })['value'])))

        yield items

    @defer.deferredGenerator
    def set_prices(self, prices):
        data = dict()
        for item, new_price in prices.iteritems():
            data['obj_id_%d' % (item.index, )] = item.id
            data['oldcost_%d' % (item.index, )] = str(item.price)
            data['cost_%d' % (item.index, )] = new_price
            data['back_to_inv[%s]' % (item.id, )] = 0

        data['type'] = 'update_prices'

        d = defer.waitForDeferred(self._account.post('process_market.phtml', data=data,
                                                     referer='market_your.phtml'))
        yield d
        page = d.getResult()
        name_col = page.find('b', text='Name')
        if not name_col:
            if page.find('b', text='There are no items in your shop!'):
                self._logger.info('No items in the shop')
                return

            raise PageParseError(page)

