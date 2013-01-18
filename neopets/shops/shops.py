from neopets.shops.neopianshops import NeopianShops, NeopianShop
from neopets.shops.wizard import Wizard

class Shops(object):
    def __init__(self, account):
        self._account = account
        self._wizard = Wizard(account)

    @property
    def wizard(self):
        return self._wizard

    def get_neopian(self, shop):
        NeopianShops.assert_valid(shop)
        return NeopianShop(self._account, shop)
