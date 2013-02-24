import os
import logging
from collections import namedtuple
from urlparse import urlparse
from urllib import urlencode
from twisted.internet.protocol import Protocol
from twisted.internet import reactor, defer
from twisted.web.client import Agent, CookieAgent, HTTPConnectionPool
from cookielib import LWPCookieJar, CookieJar
from StringIO import StringIO
from twisted.web.http_headers import Headers
from zope.interface import implements
from twisted.web.iweb import IBodyProducer



RequestData = namedtuple('RequestData', ('url', 'referer', 'data'))


class StringProducer(object):
    implements(IBodyProducer)

    def __init__(self, body):
        self.body = body
        self.length = len(body)

    def startProducing(self, consumer):
        consumer.write(self.body)
        return defer.succeed(None)

    def pauseProducing(self):
        pass

    def stopProducing(self):
        pass


class MemoryReceiver(Protocol):
    def __init__(self):
        self._finished = defer.Deferred()
        self._io = StringIO()

    @property
    def finished(self):
        return self._finished

    def dataReceived(self, data):
        self._io.write(data)

    def connectionLost(self, _):
        self._finished.callback(self._io.getvalue())
        self._io.close()


class Browser(object):
    _HEADERS = {
        'User-Agent' : ['Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_2) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1309.0 Safari/537.17', ]
    }

    _POST_HEADERS = {
        'Content-Type' : ['application/x-www-form-urlencoded', ]
    }

    def __init__(self, page_archiver, cookie_file=None):
        self._logger = logging.getLogger(__name__)
        self._page_archiver = page_archiver
        self._logger.debug('Using page archiver: %s. Cookie file: %s',
                           page_archiver is not None,
                           cookie_file)
        if cookie_file:
            umask = os.umask(077)
            cj = LWPCookieJar(cookie_file)
            os.umask(umask)
        else:
            cj = CookieJar()

        pool = HTTPConnectionPool(reactor, persistent=True)
        pool.maxPersistentPerHost = 10
        self._agent = CookieAgent(Agent(reactor, pool=pool), cj)

    @defer.deferredGenerator
    def _request(self, request_type, url, referer=None, body=None):
        self._logger.debug('Fetching %s', url)

        headers = dict(self._HEADERS)
        if referer:
            headers['Referer'] = [referer, ]

        body_prod = None
        if body:
            headers.update(self._POST_HEADERS)
            body_prod = StringProducer(body)

        d = defer.waitForDeferred(self._agent.request(request_type, url, Headers(headers),
                                                      body_prod))
        yield d
        response = d.getResult()

        receiver = MemoryReceiver()
        response.deliverBody(receiver)

        if request_type == 'POST' and (response.code >= 300 and response.code < 400):
            new_location = '%s/%s' % (
                os.path.split(url)[0],
                response.headers.getRawHeaders('location')[0])
            d = defer.waitForDeferred(self.get(new_location, referer))
            yield d
            yield d.getResult()
            return
        else:
            d = defer.waitForDeferred(receiver.finished)
            yield d
            page = d.getResult()

        yield page

    def get(self, url, referer=None):
        return self._request('GET', url, referer)

    def post(self, url, data, referer=None, manual_redirect=False):
        self._logger.debug('Posting to %s: %s', url, data)
        encoded_data = urlencode(data)
        return self._request('POST', url, referer, encoded_data)
