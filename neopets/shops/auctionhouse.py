from collections import namedtuple
from twisted.internet import defer
from neopets.utils import np_to_int
from neopets.common import PageParseError


Auction = namedtuple('Auction', ('link', 'item', 'last_bid', 'current_price', 'last_bidder'))


class AuctionHouse(object):
    def __init__(self, account):
        self._account = account

    @defer.deferredGenerator
    def get_main_page(self):
        d = defer.waitForDeferred(self._account.get('auctions.phtml'))
        yield d
        auctions_page = d.getResult()

        b = auctions_page.find('b', text='Auc No.')
        if not b:
            raise PageParseError(auctions_page)
        auctions_table = b.findParent('table')

        auctions = []
        for auction_tr in auctions_table.findAll('tr')[1:]:
            tds = auction_tr.findAll('td')

            if tds[3].find('b'):
                # Neofrinds only
                continue

            last_bidder = tds[7].text if tds[7].text != 'nobody' else None
            auctions.append(Auction(
                tds[1].find('a')['href'],
                tds[2].find('a').text,
                int(tds[5].find('b').text),
                int(tds[6].find('b').text),
                last_bidder))

        yield auctions
