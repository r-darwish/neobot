from neopianshops import NeopianShops, NeopianShop

class Shops(object):
    def __init__(self, account):
        self._account = account

    def get_neopian(self, shop):
        NeopianShops.assert_valid(shop)
        return NeopianShop(self._account, shop)
