import re
from neopets.shops.item import Item


class InvalidNeopianShopError(Exception):
    pass


class NeopianShops(object):
    _SHOP_URL = {
        'food' : 'objects.phtml?type=shop&obj_type=1',
        'magic' : 'objects.phtml?type=shop&obj_type=2',
        'toy' : 'objects.phtml?type=shop&obj_type=3',
        'clothing' : 'objects.phtml?type=shop&obj_type=4',
        'grooming' : 'objects.phtml?type=shop&obj_type=5',
        'book' : 'objects.phtml?type=shop&obj_type=7',
        'cards' : 'objects.phtml?type=shop&obj_type=8',
        'battle_magic' : 'objects.phtml?type=shop&obj_type=9',
        'defence_magic' : 'objects.phtml?type=shop&obj_type=10',
        'garden' : 'objects.phtml?type=shop&obj_type=12',
        'pharmacy' : 'objects.phtml?type=shop&obj_type=13',
        'chocolate' : 'objects.phtml?type=shop&obj_type=14',
        'bakery' : 'objects.phtml?type=shop&obj_type=15',
        'health_food' : 'objects.phtml?type=shop&obj_type=16',
        'gift_shop' : 'objects.phtml?type=shop&obj_type=17',
        'smoothie' : 'objects.phtml?type=shop&obj_type=18',
        'tropical_food' : 'objects.phtml?type=shop&obj_type=20',
        'tikitack' : 'objects.phtml?type=shop&obj_type=21',
        'grundos_cafe' : 'objects.phtml?type=shop&obj_type=22',
        'space_weaponary' : 'objects.phtml?type=shop&obj_type=23',
        'space_armour' : 'objects.phtml?type=shop&obj_type=24',
        'petpet' : 'objects.phtml?type=shop&obj_type=25',
        'robo_petpet' : 'objects.phtml?type=shop&obj_type=26',
        'rock_pool' : 'objects.phtml?type=shop&obj_type=27',
        'spooky_food' : 'objects.phtml?type=shop&obj_type=30',
        'spooky_petpet' : 'objects.phtml?type=shop&obj_type=31',
        'coffe_cave' : 'objects.phtml?type=shop&obj_type=34',
        'slushie' : 'objects.phtml?type=shop&obj_type=35',
        'ice_crystal' : 'objects.phtml?type=shop&obj_type=36',
        'icy_fun' : 'objects.phtml?type=shop&obj_type=37',
        'faerieland_bookshop' : 'objects.phtml?type=shop&obj_type=38',
        'faerie_foods' : 'objects.phtml?type=shop&obj_type=39',
        'faerieland_petpets' : 'objects.phtml?type=shop&obj_type=40',
        'furniture' : 'objects.phtml?type=shop&obj_type=41',
        'tyrannian_foods' : 'objects.phtml?type=shop&obj_type=42',
        'tyrannian_furnitures' : 'objects.phtml?type=shop&obj_type=43',
        'tyrannian_petpets' : 'objects.phtml?type=shop&obj_type=44',
        'tyrannian_weaponary' : 'objects.phtml?type=shop&obj_type=45',
        'hotdogs' : 'objects.phtml?type=shop&obj_type=46',
        'pizaroo' : 'objects.phtml?type=shop&obj_type=47',
        'usukiland' : 'objects.phtml?type=shop&obj_type=48',
        'desert_foods' : 'objects.phtml?type=shop&obj_type=49',
        'peopatra_petpets' : 'objects.phtml?type=shop&obj_type=50',
        'scrolls' : 'objects.phtml?type=shop&obj_type=51',
        'school' : 'objects.phtml?type=shop&obj_type=53',
    }

    @classmethod
    def assert_valid(cls, shop):
        if shop not in cls._SHOP_URL:
            raise InvalidNeopianShopError()

    @classmethod
    def url_of(cls, shop):
        cls.assert_valid(shop)
        return cls._SHOP_URL[shop]


class NeopianShop(object):
    _HAGGLE_RE = re.compile(r'haggle\.phtml')
    _STOCK_RE = re.compile(r'([\d,]+) in stock')
    _COST_RE = re.compile(r'Cost: ([\d,]+) NP')

    def __init__(self, account, shop):
        self._account = account
        self._shop = shop
        self._url = NeopianShops.url_of(shop)
        self._name = shop

    @property
    def name(self):
        return self._name

    def get_items(self):
        d = self._account.get(self._url)
        d.addCallback(self._on_shop)
        return d

    def _on_shop(self, page):
        for item_link in page.findAll('a', attrs=dict(href=self._HAGGLE_RE)):
            item_name_elem = item_link.parent.find('b')
            item_name = item_name_elem.text

            in_stock_elem = item_name_elem.nextSibling.nextSibling
            in_stock = int(self._STOCK_RE.search(in_stock_elem).group(1))

            price_elem = in_stock_elem.nextSibling.nextSibling
            price = int(
                self._COST_RE.search(price_elem).group(1).replace(',',''))

            yield Item(item_name, in_stock, price, item_link.attrMap['href'])
