from collections import namedtuple
from twisted.internet import defer
from neopets.utils import np_to_int
from neopets.common import PageParseError


Auction = namedtuple('Auction', ('link', 'item', 'last_bid', 'current_price', 'last_bidder'))

Bidder = namedtuple('Bidder', ('name', 'bid'))

AuctionDetails = namedtuple('AuctionDetails', ('open', 'next_bid', 'bidders'))

class AuctionHouse(object):
    def __init__(self, account):
        self._account = account

    @defer.deferredGenerator
    def get_main_page(self, page=0):
        d = defer.waitForDeferred(
            self._account.get('auctions.phtml?auction_counter=%d' % (page * 20)))
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

    @defer.deferredGenerator
    def get_auction_page(self, link):
        d = defer.waitForDeferred(self._account.get(link))
        yield d
        page = d.getResult()

        head = page.find('b', text='Bidder')
        if not head:
            raise PageParseError(page)

        bidders = []
        table = head.findParent('table')
        for tr in table.findAll('tr')[1:]:
            tds = tr.findAll('td')
            bidders.append(Bidder(tds[0].text, np_to_int(tds[1].find('b').text)))


        auction_open = page.find('b', text='Time Left in Auction : ').parent.nextSibling.strip() != 'Closed'
        if auction_open:
            next_bid = int(page.find('input', attrs={'type' : 'text', 'name' : 'amount'})['value'])
        else:
            next_bid = None

        yield AuctionDetails(auction_open, next_bid, bidders)
