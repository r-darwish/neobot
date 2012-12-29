import re
import logging
from neopets.common import PageParseError


class HideNSeek(object):
    _WIN_RE = re.compile(r'you will have to refresh the main page to see your winnings!')

    def __init__(self, account):
        self._account = account

    def __str__(self):
        return 'Hide & Seek'

    def run(self):
        logging.info('Starting Hide & Seek')
        return self._start_game()

    def _start_game(self):
        d = self._account.get('objects.phtml?type=inventory')
        d.addCallback(self._on_logged_in)
        return d

    def _on_logged_in(self, page):
        d = self._account.get('games/hidenseek/27.phtml')
        d.addCallback(self._on_start_game)
        return d

    def _on_start_game(self, page):
        areas = page.findAll('area')
        if not areas:
            raise PageParseError(page)

        self._links = set()
        for area in areas:
            for key, value in area.attrs:
                if key == 'href':
                    self._links.add(str(value))
                    break

        return self._try_link()

    def _try_link(self):
        link = self._links.pop()
        d = self._account.get(link, referer='games/hidenseek/27.phtml')
        d.addCallback(self._on_link)
        return d

    def _on_link(self, page):
        if 0 == len(page):
            logging.warning('Zero length page')
            return self._try_link()

        if page.find(text='(you did not find xpsyghost... click here to go back)') or \
           page.find(text='Ha ha!  You have already looked there!'):
            return self._try_link()

        if page.find(text='Im SO BORED of Kacheek Seek... let\'s play something else!'):
            logging.info('Done Playing')
            return

        if not page.find(text=self._WIN_RE):
            raise PageParseError(page)

        b = page.findAll('b')

        logging.info('Won %s NP', b[1].text)
        return self._on_logged_in(page)
