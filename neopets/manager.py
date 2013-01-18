import logging
import time
import os
from twisted.internet.defer import Deferred
from neopets.account import Account
from neopets.database import get_engine
from neopets.common import PageParseError
from neopets import games
from neopets import dailies
from neopets.page_archiver import PageArchiver
from neopets.browser import Browser


class Manager(object):
    def __init__(self, config):
        self._logger = logging.getLogger(__name__)
        self._config = config
        self._bad_pages_dir = os.path.join(
            self._config.misc.data_dir, 'bad_pages')

        self._db = get_engine(self._config.misc.data_dir)

        if self._config.misc.page_archiver:
            self._pages_dir = os.path.join(
                self._config.misc.data_dir, 'pages')
            page_archiver = PageArchiver(
                self._pages_dir, self._db)
        else:
            self._pages_dir = None
            page_archiver = None

        self._account = Account(
            self._config.misc.data_dir,
            self._config.account.username,
            self._config.account.password,
            page_archiver)

        self._outside_browser = Browser(
            page_archiver)

        self._finished = Deferred()

        self._tasks = [
            dailies.Interest(self._account),
            dailies.ShopTill(self._account),
            dailies.Tombola(self._account),
            games.DailyPuzzle(self._account, self._outside_browser),
            games.PotatoCounter(self._account),
            games.Cliffhanger(self._account),
            games.HideNSeek(self._account),
        ]

    @staticmethod
    def _create_directory(directory):
        if directory is None:
            return

        if not os.path.isdir(directory):
            os.mkdir(directory)

    def run(self):
        for directory in (self._bad_pages_dir,
                          self._pages_dir):
            self._create_directory(directory)

        self._run_next_task()
        return self._finished

    def _run_next_task(self):
        if not self._tasks:
            self._logger.info('No more tasks')
            self._finished.callback(None)
            return

        task = self._tasks.pop(0)
        self._logger.info('Starting %s', task)
        d = task.run()
        d.addCallback(self._on_task_done, str(task))
        d.addErrback(self._on_task_error, str(task))

    def _dump_page_error(self, page, traceback):
        name = os.path.join(self._bad_pages_dir, str(time.time()))
        with open(name + '.html', 'w') as page_file:
            page_file.write(str(page))

        with open(name + '.tbk', 'w') as tb_file:
            tb_file.write(traceback)

    def _on_task_done(self, _, task_name):
        self._logger.info('Task %s finished successfully', task_name)
        return self._run_next_task()

    def _on_task_error(self, error, task_name):
        self._logger.error("Task %s failed: %s", task_name, error)

        e = error.value
        if type(e) is PageParseError:
            self._dump_page_error(e.page, error.getTraceback())
        return self._run_next_task()
