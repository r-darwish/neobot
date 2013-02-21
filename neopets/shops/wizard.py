import re
from collections import namedtuple
from twisted.internet import defer
from neopets.utils import to_int, np_to_int


Offer = namedtuple('Offer', ('shop_link', 'item', 'stock', 'price'))


class ShopWizardExhaustedError(Exception):
    def __init__(self, resume_time):
        super(ShopWizardExhaustedError, self).__init__(
            'Shop wizard says to come back in %d minutes' % (resume_time))
        self._resume_time = resume_time

    @property
    def resume_time(self):
        return self._resume_time


class Wizard(object):
    _SHOP_LINKS = re.compile(r'browseshop\.phtml')
    _LINK_ATTRS = dict(href=_SHOP_LINKS)

    def __init__(self, account):
        self._account = account

    @defer.deferredGenerator
    def get_offers(self, item):
        d = defer.waitForDeferred(self._account.post(
            'market.phtml', data=dict(
                type='process_wizard', feedset='0', shopwizard=item,
                table='shop', criteria='exact', min_price='0',
                max_price='99999'),
            referer='market.phtml?type=wizard'))
        yield d

        page = d.getResult()
        too_many = page.find('b', text='Whoa there, too many searches!')
        if too_many:
            back = page.find(text=re.compile('I am too busy right now')). \
                   nextSibling.nextSibling.nextSibling.text
            raise ShopWizardExhaustedError(int(back))

        offers = []
        for link in page.findAll('a', attrs=self._LINK_ATTRS):
            tr = link.parent.parent
            tds = tr.findAll('td')
            item_name = tds[1].text
            stock = to_int(tds[2].text)
            price = np_to_int(tds[3].text)

            offers.append(Offer(link.attrMap['href'], item_name, stock, price))

        yield offers

