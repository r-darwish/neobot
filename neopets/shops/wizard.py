import logging
import re
from collections import namedtuple
from twisted.internet import defer
from neopets.utils import to_int, np_to_int


Offer = namedtuple('Offer', ('shop_link', 'item', 'stock', 'price', 'owner'))


class ItemNotFoundInShopWizardError(Exception):
    def __init__(self, item):
        super(ItemNotFoundInShopWizardError, self).__init__(
            'Item %s not found in shop wizard' % (item, ))


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
    _SECTIONS = (
        frozenset(('a', 'n', '0')),
        frozenset(('b', 'o', '1')),
        frozenset(('c', 'p', '2')),
        frozenset(('d', 'q', '3')),
        frozenset(('e', 'r', '4')),
        frozenset(('f', 's', '5')),
        frozenset(('g', 't', '6')),
        frozenset(('h', 'u', '7')),
        frozenset(('i', 'v', '8')),
        frozenset(('j', 'w', '9')),
        frozenset(('k', 'x', '_')),
        frozenset(('l', 'y')),
        frozenset(('m', 'z')))

    def __init__(self, account):
        self._account = account
        self._logger = logging.getLogger(__name__)
        self._my_section = self.get_section(account.username[0])

    @property
    def my_section(self):
        return self._my_section

    @classmethod
    def get_section(cls, letter):
        letter = letter.lower()
        for sec in cls._SECTIONS:
            if letter in sec:
                return sec
        else:
            raise Exception('No section for %s', letter)

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

        letters = set()

        offers = []
        for link in page.findAll('a', attrs=self._LINK_ATTRS):
            tr = link.parent.parent
            tds = tr.findAll('td')
            item_name = tds[1].text
            stock = to_int(tds[2].text)
            price = np_to_int(tds[3].text)
            owner = link.text
            letters.add(owner[0].lower())

            offers.append(Offer(link.attrMap['href'], item_name, stock, price, owner))

        if len(offers) == 0:
            raise ItemNotFoundInShopWizardError(item)

        yield offers, frozenset(letters)

    @defer.deferredGenerator
    def get_offers_from_section(self, item, section):
        while True:
            d = defer.waitForDeferred(self.get_offers(item))
            yield d
            offers, fetched_section = d.getResult()

            if len(fetched_section - section) == 0:
                yield offers
                return

            self._logger.debug('Fetch section %s, which is not our section', fetched_section)
