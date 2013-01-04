import logging
from BeautifulSoup import BeautifulSoup
from neopets.browser import Browser


class LoginError(Exception):
    def __init__(self, page):
        super(LoginError, self).__init__()
        self.page = page


class Account(object):
    def __init__(self, username, password):
        self._browser = Browser()
        self._username = username
        self._password = password

    def get(self, url, referer=None):
        if referer:
            referer = 'http://www.neopets.com/' + referer

        d = self._browser.get('http://www.neopets.com/' + url,
                              referer)
        d.addCallback(self._on_page)
        return d

    def post(self, url, data, referer=None):
        if referer:
            referer = 'http://www.neopets.com/' + referer

        d = self._browser.post('http://www.neopets.com/' + url,
                               data, referer)
        d.addCallback(self._on_page)
        return d

    def _on_page(self, page):
        if not page:
            import ipdb
            ipdb.set_trace()

        soup = BeautifulSoup(page)
        if not soup.find('a', text='Log in'):
            return soup

        logging.info('Need to login. Using account %s', self._username)
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
