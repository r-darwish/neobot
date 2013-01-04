import logging
import time
import os
from twisted.internet.defer import Deferred
from neopets.account import Account
from neopets.common import PageParseError
from neopets import games
from neopets import dailies


class Manager(object):
    def __init__(self, config):
        self._config = config
        self._bad_pages_dir = os.path.join(
            self._config.misc.data_dir, 'bad_pages')

        self._account = Account(
            self._config.account.username,
            self._config.account.password)

        self._finished = Deferred()

        self._tasks = [
            dailies.Interest(self._account),
            dailies.Tombola(self._account),
            games.Cliffhanger(self._account),
            games.HideNSeek(self._account),
        ]


    def run(self):
        if not os.path.isdir(self._bad_pages_dir):
            os.mkdir(self._bad_pages_dir)


        self._run_next_task()
        return self._finished

    def _run_next_task(self):
        if not self._tasks:
            logging.info('No more tasks')
            self._finished.callback(None)
            return

        task = self._tasks.pop(0)
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
        logging.info('Task %s finished successfully', task_name)
        return self._run_next_task()

    def _on_task_error(self, error, task_name):
        logging.error("Task %s failed: %s", task_name, error)

        e = error.value
        if type(e) is PageParseError:
            self._dump_page_error(e.page, error.getTraceback())
        return self._run_next_task()
