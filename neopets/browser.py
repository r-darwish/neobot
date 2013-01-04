import os
import logging
from urlparse import urlparse
from urllib import urlencode
from zope.interface import implements
from twisted.web.iweb import IBodyProducer
from twisted.internet import reactor, defer
from twisted.internet.defer import succeed
from twisted.internet.protocol import Protocol, connectionDone
from twisted.web.client import Agent, ResponseDone
from twisted.web.http_headers import Headers


class UnknownHttpCodeError(Exception):
    def __init__(self, code):
        super(UnknownHttpCodeError, self).__init__(
            'Unknown HTTP code %d' % (code, ))
        self.code = code


class PageGetter(Protocol):
    def __init__(self):
        self._finished = defer.Deferred()
        self._buffer = ''

    @property
    def finished(self):
        return self._finished

    def dataReceived(self, data):
        self._buffer += data

    def connectionLost(self, reason=connectionDone):
        reason.trap(ResponseDone)
        self._finished.callback(self._buffer)


class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class Browser(object):
    _HEADERS = {
        'User-Agent' : ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1309.0 Safari/537.17']
    }

    _POST_HEADERS = {
        'User-Agent' : ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1309.0 Safari/537.17'],
        'Content-Type' : ['application/x-www-form-urlencoded']
    }

    def __init__(self):
        self._cookies = dict()
        self._agent = Agent(reactor)

    def get(self, url, referer=None):
        logging.debug('Fetching %s', url)
        headers = dict(self._HEADERS)
        headers['Cookie'] = [';'.join([key + '=' + value for key, value
                                       in self._cookies.iteritems()])]
        if referer:
            headers['Referer'] = [referer, ]

        d = self._agent.request(
            method='GET',
            uri=url,
            headers=Headers(headers))
        d.addCallback(self._on_connected, urlparse(url))
        d.addErrback(self._on_error, url)
        return d

    def post(self, url, data, referer=None):
        logging.debug('Posting to %s: %s', url, data)
        headers = dict(self._POST_HEADERS)
        headers['Cookie'] = [';'.join([key + '=' + value for key, value
                                       in self._cookies.iteritems()])]
        if referer:
            headers['Referer'] = [referer, ]
        encoded_data = urlencode(data)
        d = self._agent.request(
            'POST',
            url,
            Headers(headers),
            StringProducer(encoded_data) if encoded_data else None)
        d.addCallback(self._on_connected, urlparse(url))
        d.addErrback(self._on_error, url)
        return d

    def _on_connected(self, result, url):
        if result.headers.hasHeader('Set-Cookie'):
            for cookie in result.headers.getRawHeaders('Set-Cookie'):
                kv = cookie.split(';')[0]
                key, value = kv.split('=')
                self._cookies[key] = value

        if result.code == 302:
            redirection = result.headers.getRawHeaders('location')[0]
            if redirection.startswith('/'):
                new_location = 'http://%s%s' % (url.hostname, redirection)
            else:
                new_location = 'http://%s%s/%s' % (
                    url.hostname, os.path.split(url.path)[0],
                    redirection)
            logging.debug('Redirected to %s', new_location)
            return self.get(new_location)
        elif result.code == 200:
            pg = PageGetter()
            result.deliverBody(pg)
            return pg.finished
        else:
            raise UnknownHttpCodeError(result.code)

    def _on_error(self, error, url):
        logging.error('Error fetching %s: %s', error, url)
