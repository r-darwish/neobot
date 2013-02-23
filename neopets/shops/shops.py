from neopets.shops.neopianshops import NeopianShops, NeopianShop
from neopets.shops.wizard import Wizard
from neopets.shops.auctionhouse import AuctionHouse
from neopets.shops.pricecalc import EstPriceCalculator

class Shops(object):
    def __init__(self, account, cache):
        self._account = account
        self._wizard = Wizard(account)
        self._auction_house = AuctionHouse(account)
        self._est_price_calc = EstPriceCalculator(self)
        self._est_price_calc.calc = cache.cache(self._est_price_calc.calc)

    @property
    def est_price_calc(self):
        return self._est_price_calc

    @property
    def auction_house(self):
        return self._auction_house

    @property
    def wizard(self):
        return self._wizard

    def get_neopian(self, shop):
        NeopianShops.assert_valid(shop)
        return NeopianShop(self._account, shop)
