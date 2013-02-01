import logging
from twisted.internet.defer import Deferred

class SerialTasks(object):
    def __init__(self, tasks, group_name, error_callback=None):
        self._logger = logging.getLogger(__name__ + '.SerialTasks(%s)' % (group_name, ))
        self._tasks = tasks
        self._done = Deferred()
        self._error_callback = error_callback

    def _run_next_task(self):
        try:
            task = self._tasks.pop(0)
        except IndexError:
            self._logger.info('All tasks finished')
            self._done.callback(None)
        else:
            self._logger.info('Starting task \'%s\'', task)
            d = task.run()
            d.addCallback(self._on_success, str(task))
            d.addErrback(self._on_error, str(task))

    def run(self):
        self._run_next_task()
        return self._done

    def _on_success(self, _, task_name):
        self._logger.info('Task \'%s\' finished successfully', task_name)
        self._run_next_task()

    def _on_error(self, result, task_name):
        self._logger.info('Task \'%s\' encountered an error: %s', task_name, result)
        if self._error_callback is not None:
            self._error_callback(result)
        self._run_next_task()
