import logging
import re
from neopets.common import PageParseError


class ShopTill(object):
    _CURRENTLY_HAVE_RE = re.compile(r'You currently have ')
    _NP_RE = re.compile(r'([\d,]+) NP')

    def __init__(self, account):
        self._logger = logging.getLogger(__name__)
        self._account = account

    def __str__(self):
        return 'Shop till'

    def run(self):
        d = self._account.get('market.phtml?type=till')
        d.addCallback(self._on_page)
        return d

    def _on_page(self, page):
        currently_have = page.find(text=self._CURRENTLY_HAVE_RE)
        if not currently_have:
            raise PageParseError(page)

        np_string = currently_have.parent()[0].text
        np = int(self._NP_RE.search(np_string).group(1).replace(',', ''))

        if np == 0:
            self._logger.info('Shop till is empty')
            return

        self._logger.info('There are %d NP in the shop till', np)
        d = self._account.post('process_market.phtml',
                               data=dict(type='withdraw', amount=str(np)),
                               referer='market.phtml?type=till')
        d.addCallback(self._on_page)
        return d
