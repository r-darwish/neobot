import os
import logging
import shelve
from collections import namedtuple
from urlparse import urlparse
from urllib import urlencode
from twisted.web.client import getPage


RequestData = namedtuple('RequestData', ('url', 'referer', 'data'))


class Browser(object):
    _AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1309.0 Safari/537.17"

    _POST_HEADERS = {
        'Content-Type' : 'application/x-www-form-urlencoded'
    }

    def __init__(self, page_archiver, cookie_file=None):
        self._logger = logging.getLogger(__name__)
        self._page_archiver = page_archiver
        self._logger.debug('Using page archiver: %s. Cookie file: %s',
                           page_archiver is not None,
                           cookie_file)
        if cookie_file:
            umask = os.umask(077)
            self._cookies = shelve.open(cookie_file, writeback=False)
            os.umask(umask)
        else:
            self._cookies = dict()

    def get(self, url, referer=None):
        self._logger.debug('Fetching %s', url)

        headers = dict()
        if referer:
            headers['Referer'] = referer

        d = getPage(
            url,
            headers=headers,
            agent=self._AGENT,
            cookies=self._cookies)
        d.addCallback(self._on_download, RequestData(
            urlparse(url), referer, None))
        d.addErrback(self._on_error, url)
        return d

    def post(self, url, data, referer=None, manual_redirect=False):
        self._logger.debug('Posting to %s: %s', url, data)

        headers = dict(self._POST_HEADERS)
        if referer:
            headers['Referer'] = referer

        encoded_data = urlencode(data)
        d = getPage(
            url,
            method='POST',
            headers=headers,
            agent=self._AGENT,
            cookies=self._cookies,
            postdata=encoded_data,
        followRedirect=not manual_redirect)

        d.addCallback(self._on_download, RequestData(
            urlparse(url), referer, data))
        if manual_redirect:
            d.addErrback(self._redirection_handler, url)
        d.addErrback(self._on_error, url)
        return d

    def _redirection_handler(self, result, url):
        new_location = '%s/%s' % (
            os.path.split(url)[0],
            result.value.location)
        return self.get(new_location)

    def _on_download(self, page, request_data):
        if self._page_archiver:
            self._page_archiver.archive(
                page, request_data.url, request_data.data, request_data.referer)
        return page

    def _on_error(self, error, url):
        self._logger.error('Error fetching %s: %s', error, url)
        return error
