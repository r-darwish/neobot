import re
import logging
from collections import namedtuple
from twisted.internet import defer
from neopets.utils import np_to_int
from neopets.common import PageParseError

class BidError(Exception):
    pass

Auction = namedtuple('Auction', ('link', 'item', 'last_bid', 'current_price', 'last_bidder', 'id'))

Bidder = namedtuple('Bidder', ('name', 'bid'))

AuctionDetails = namedtuple('AuctionDetails', ('open', 'next_bid', 'bidders', 'refcode'))

class AuctionHouse(object):
    _ID_RE = re.compile(r'auction_id=(\d+)')
    _WAIT_RE = re.compile(r'You must wait a few more seconds before you can bid on this auction again!')
    _RACE_RE = re.compile(r'This means you have to bid at least')
    _CLOSE_RE = re.compile(r'This auction is closed')

    def __init__(self, account):
        self._account = account
        self._logger = logging.getLogger(__name__)

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

            link = tds[1].find('a')['href']
            auction_id = self._ID_RE.search(link).group(1)
            last_bidder = tds[7].text if tds[7].text != 'nobody' else None

            auctions.append(Auction(
                link,
                tds[2].find('a').text,
                int(tds[5].find('b').text),
                int(tds[6].find('b').text),
                last_bidder,
                auction_id))

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
            refcode = page.find('input', attrs={'name' : '_ref_ck'})['value']
        else:
            next_bid = None
            refcode = None

        yield AuctionDetails(auction_open, next_bid, bidders, refcode)

    @defer.deferredGenerator
    def bid(self, auction_id, price, refcode):
        self._logger.debug('Bidding %d in auction %s', price, auction_id)
        d = defer.waitForDeferred(self._account.post(
            'auctions.phtml?type=placebid',
            data={'auction_id' : auction_id, 'amount' : str(price), '_ref_ck' : refcode }))
        yield d

        page = d.getResult()
        if not page.find('b', text='BID SUCCESSFUL'):
            if page.find('p', text=self._WAIT_RE):
                self._logger.warning('Bidding %s cause the \'you must wait\' response')
                return

            if page.find('p', text=self._RACE_RE):
                self._logger.warning('Someone else bidded higher than us')
                return

            if page.find('p', text=self._CLOSE_re):
                self._logger.error('Auction is closed')
                return

            import ipdb
            ipdb.set_trace()
            raise BidError()
