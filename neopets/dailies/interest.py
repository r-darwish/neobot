import re
import logging

class Interest(object):
    _COLLECT_BUTTON = re.compile(r'Collect Interest.*')

    def __init__(self, account):
        self._logger = logging.getLogger(__name__)
        self._account = account

    def run(self):
        d = self._account.get('bank.phtml')
        d.addCallback(self._on_bank_page)
        return d

    def _on_bank_page(self, page):
        collect_button = page.find('input', value=self._COLLECT_BUTTON)
        if not collect_button:
            self._logger.info('No collect button is present')
            return

        d = self._account.post('process_bank.phtml', dict(type='interest'), manual_redirect=True)
        d.addCallback(self._on_submit)
        return d

    def _on_submit(self, _):
        self._logger.info('Done')

    def __str__(self):
        return 'Daily interest'
