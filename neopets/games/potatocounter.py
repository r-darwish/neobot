import re
import logging
from neopets.common import PageParseError


class PotatoCounter(object):
    _POTATO_RE = re.compile(r'.*potato.*\.gif')
    _POTATO_ATTRS = dict(src=_POTATO_RE)

    def __init__(self, account):
        self._account = account

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
        import ipdb
        ipdb.set_trace()
        return d

    def _on_submit(self, page):
        import ipdb
        ipdb.set_trace()
