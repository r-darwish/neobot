import logging
import time
import os
import traceback
from twisted.internet import defer
from neopets.sniper import SniperManager
from neopets.account import Account
from neopets.database import get_engine
from neopets.tasks import SerialTasks
from neopets.common import PageParseError
from neopets import games
from neopets import dailies
from neopets.shops import Shops
from neopets.page_archiver import PageArchiver
from neopets.browser import Browser
from neopets.cache import QueryCache
from neopets.autopricer import AutoPricer


class Manager(object):
    def __init__(self, config):
        self._logger = logging.getLogger(__name__)
        self._config = config
        self._bad_pages_dir = os.path.join(
            self._config.misc.data_dir, 'bad_pages')
        self._cache_dir = os.path.join(
            self._config.misc.data_dir, 'cache')
        self._auctions_dir = os.path.join(
            self._config.misc.data_dir, 'auctions')


        self._db = get_engine(self._config.misc.data_dir)

        if self._config.misc.page_archiver:
            self._pages_dir = os.path.join(
                self._config.misc.data_dir, 'pages')
            page_archiver = PageArchiver(
                self._pages_dir, self._db)
        else:
            self._pages_dir = None
            page_archiver = None

        for directory in (self._bad_pages_dir,
                          self._pages_dir,
                          self._cache_dir,
                          self._auctions_dir):
            self._create_directory(directory)

        self._account = Account(
            self._config.misc.data_dir,
            self._config.account.username,
            self._config.account.password,
            page_archiver)

        self._outside_browser = Browser(
            page_archiver)

        self._cache = QueryCache(self._cache_dir)
        self._shops = Shops(self._account, self._cache)

        self._dailies = [
            dailies.Shrine(self._account),
            dailies.Interest(self._account),
            dailies.ShopTill(self._account),
            dailies.Tombola(self._account),
            games.DailyPuzzle(self._account, self._outside_browser),
            games.PotatoCounter(self._account),
            games.Cliffhanger(self._account),
            games.HideNSeek(self._account),
        ]

        self._sniper = SniperManager(self._account, self._shops, self._config.sniper,
                                     self._auctions_dir)
        self._sniper.on_deal.register(self._on_deal)
        self._autopricer = AutoPricer(self._account, self._shops)

    def _on_deal(self, auction, price):
        self._logger.info('Deal! %s (%d)', auction, price)

    @staticmethod
    def _create_directory(directory):
        if directory is None:
            return

        if not os.path.isdir(directory):
            os.mkdir(directory)

    @defer.deferredGenerator
    def run(self):
        if self._config.application.dailies:
            all_tasks = defer.waitForDeferred(
                SerialTasks(self._dailies, "Dailies", self._error_callback).run())
            yield all_tasks
            all_tasks.getResult()

        self._logger.info('Starting autopricer')
        d = defer.waitForDeferred(self._autopricer.run())
        yield d

        try:
            d.getResult()
        except Exception as e:
            self._logger.error('Autopricer error: %s', traceback.format_exc(e))
        else:
            self._logger.info('Autopricer done')

        if self._config.application.sniper:
            self._sniper.run()
            yield defer.waitForDeferred(defer.Deferred())

        yield None

    def _dump_page_error(self, page, traceback):
        name = os.path.join(self._bad_pages_dir, str(time.time()))
        with open(name + '.html', 'w') as page_file:
            page_file.write(str(page))

        with open(name + '.tbk', 'w') as tb_file:
            tb_file.write(traceback)

    def _error_callback(self, error):
        e = error.value
        if type(e) is PageParseError:
            self._dump_page_error(e.page, error.getTraceback())
