import re
import logging
from neopets.common import PageParseError


class Tombola(object):
    _PLAY_BUTTON_ATTRS = dict(value='Play Tombola!')
    _POST_DATA = dict()
    _PRIZE_RE = re.compile('Your Prize - (.*)')
    _SORRY_RE = re.compile(
        r'Sorry, you are only allowed one Tombola free spin every day')
    _WINNER_RE = re.compile(r'YOU ARE A WINNER!!!')
    _YOU_WIN_RE = re.compile(r'You Win (\d+) Neopoints')

    def __init__(self, account):
        self._logger = logging.getLogger(__name__)
        self._account = account

    def __str__(self):
        return 'Tombola'

    def run(self):
        d = self._account.get('island/tombola.phtml')
        d.addCallback(self._on_main_page)
        return d

    def _on_main_page(self, page):
        if not page.find('input', attrs=self._PLAY_BUTTON_ATTRS):
            self._logger.info('Not playable')
            return

        d = self._account.post('island/tombola2.phtml',
                               self._POST_DATA,
                               'island/tombola.phtml')
        d.addCallback(self._on_submit)
        return d

    def _on_submit(self, page):
        prize = page.find(text=self._PRIZE_RE)
        winner = page.find(text=self._WINNER_RE)
        if winner:
            np = page.find(text=self._YOU_WIN_RE)
            if not np:
                raise PageParseError(page)

            np = self._YOU_WIN_RE.search(np).group(1)
            self._logger.info('Won %s NP and maybe some items', np)
        elif prize:
            prize = self._PRIZE_RE.search(prize).group(1)
            self._logger.info('Prize is %s', prize)
        else:
            if page.find(text='Oh dear, that\'s not a winning ticket :('):
                self._logger.info('Didn\'t win')
            elif page.find(text=self._SORRY_RE):
                self._logger.info('Already played today')
            else:
                raise PageParseError(page)
