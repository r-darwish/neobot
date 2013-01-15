class Item(object):
    def __init__(self, name, in_stock, price, url):
        self._name = name
        self._in_stock = in_stock
        self._price = price
        self._url = url

    def __str__(self):
        return self._name

    def __repr__(self):
        return '<\'%s\' Stock: %d, Price: %d>' % (self._name, self._in_stock,
                                              self._price)
    @property
    def name(self):
        return self._name

    @property
    def in_stock(self):
        return self._in_stock

    @property
    def price(self):
        return self._price

    @property
    def url(self):
        return self._url
