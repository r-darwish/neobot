import re
import logging
from neopets.common import PageParseError


class PotatoCounter(object):
    _POTATO_RE = re.compile(r'.*potato[0-9]\.gif')
    _POTATO_ATTRS = dict(src=_POTATO_RE)
    _WINNING_RE = re.compile(r'which means you win')

    def __init__(self, account):
        self._logger = logging.getLogger(__name__)
        self._account = account

    def __str__(self):
        return 'Potato Counter'

    def run(self):
        return self._start_game()

    def _start_game(self):
        d = self._account.get('medieval/potatocounter.phtml')
        d.addCallback(self._on_start_game)
        return d

    def _on_start_game(self, page):
        potatos = len(page.findAll('img', attrs=self._POTATO_ATTRS))
        d = self._account.post('medieval/potatocounter.phtml',
                               dict(type='guess', guess=str(potatos)))
        d.addCallback(self._on_submit)
        return d

    def _on_submit(self, page):
        if page.find(
                text='Arr, you can only guess me potatoes three times a day!'):
            self._logger.info('Done playing')
            return

        winning = page.find(text=self._WINNING_RE)
        if not winning:
            raise PageParseError(page)

        neopoints = int(winning.nextSibling.text)
        self._logger.info('Won %d NP', neopoints)

        return self._start_game()
