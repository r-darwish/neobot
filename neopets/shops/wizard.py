import re
from neopets.utils import to_int, np_to_int
from collections import namedtuple


Offer = namedtuple('Offer', ('shop_link', 'item', 'stock', 'price'))


class Wizard(object):
    _SHOP_LINKS = re.compile(r'browseshop\.phtml')
    _LINK_ATTRS = dict(href=_SHOP_LINKS)

    def __init__(self, account):
        self._account = account

    def get_offers(self, item):
        d = self._account.post(
            'market.phtml', data=dict(
                type='process_wizard', feedset='0', shopwizard=item,
                table='shop', criteria='exact', min_price='0',
                max_price='99999'),
            referer='market.phtml?type=wizard')
        d.addCallback(self._on_page)
        return d

    def _on_page(self, page):
        offers = []
        for link in page.findAll('a', attrs=self._LINK_ATTRS):
            tr = link.parent.parent
            tds = tr.findAll('td')
            item_name = tds[1].text
            stock = to_int(tds[2].text)
            price = np_to_int(tds[3].text)

            offers.append(Offer(link.attrMap['href'], item_name, stock, price))

        return offers

    def _on_error(self, result, finished):
        finished.errback(result)
