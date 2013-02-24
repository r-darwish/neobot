import logging
from neopets.common import PageParseError
from twisted.internet import defer


class Shrine(object):
    def __init__(self, account):
        self._logger = logging.getLogger(__name__)
        self._account = account

    def __str__(self):
        return 'Coltzen\'s Shrine'

    @defer.deferredGenerator
    def run(self):
        d = defer.waitForDeferred(self._account.get('desert/shrine.phtml'))
        yield d
        page = d.getResult()

        submit = page.find('input', attrs={'type' : 'submit', 'value' : 'Approach the Shrine'})
        if not submit:
            raise PageParseError(page)

        d = defer.waitForDeferred(self._account.post('desert/shrine.phtml', {'type' : 'approach'},
                                                     'desert/shrine.phtml',
                                                     manual_redirect=True))
        yield d
        page = d.getResult()

        nothing = page.find('b', text='Nothing happens.')
        if nothing:
            self._logger.info('Nothing happens')
            return

        self._logger.info('Something happned')
