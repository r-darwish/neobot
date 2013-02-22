import os
import logging
from BeautifulSoup import BeautifulSoup
from neopets.browser import Browser


class LoginError(Exception):
    def __init__(self, page):
        super(LoginError, self).__init__()
        self.page = page


class Account(object):
    def __init__(self, data_dir, username, password, page_archiver):
        cookie_file = os.path.join(data_dir, 'cookies')
        self._logger = logging.getLogger(__name__)
        self._browser = Browser(page_archiver, cookie_file)
        self._username = username
        self._password = password

    @property
    def username(self):
        return self._username

    def get(self, url, referer=None):
        if referer:
            referer = 'http://www.neopets.com/' + referer

        d = self._browser.get('http://www.neopets.com/' + url,
                              referer)
        d.addCallback(self._on_page)
        return d

    def post(self, url, data, referer=None, manual_redirect=None):
        if referer:
            referer = 'http://www.neopets.com/' + referer

        d = self._browser.post('http://www.neopets.com/' + url,
                               data, referer, manual_redirect=manual_redirect)
        d.addCallback(self._on_page)
        return d

    def _on_page(self, page):
        if not page:
            import ipdb
            ipdb.set_trace()

        soup = BeautifulSoup(page)
        if not soup.find('a', text='Log in'):
            event = soup.find('b', text='Something has happened!')
            if event:
                cell = event.findParent('table').findAll('td')[2]
                text = ''.join([x.text if hasattr(x, 'text') else x
                        for x in cell.childGenerator()])
                self._logger.info("Something has happned: %s", text)

            return soup

        self._logger.info('Need to login. Using account %s', self._username)
        data = dict(username=self._username, password=self._password,
                    destination=soup.find(
                        'input', attrs=dict(name='destination'))['value'])
        d = self._browser.post('http://www.neopets.com/login.phtml', data)
        d.addCallback(self._on_login)
        return d

    def _on_login(self, page):
        soup = BeautifulSoup(page)
        if soup.find('a', text='Log in'):
            raise LoginError(page)

        return soup
