import re
import logging


class PotatoCounter(object):
    _POTATO_RE = re.compile(r'.*potato[0-9]\.gif')
    _POTATO_ATTRS = dict(src=_POTATO_RE)

    def __init__(self, account):
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
            logging.info('Done playing')
            return

        import ipdb
        ipdb.set_trace()
