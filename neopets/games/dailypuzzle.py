import logging
import re
import datetime
from BeautifulSoup import BeautifulSoup
from neopets.common import PageParseError


class NoAnswerError(Exception):
    pass


class DailyPuzzle(object):
    _ANSWER_DATE_RE = re.compile(r'The Daily Puzzle for')
    _AWARD_RE = re.compile('You have been awarded')
    _POLL_FORM_ATTRS = dict(action='/community/index.phtml')

    def __init__(self, account, outside_browser):
        self._account = account
        self._outside_browser = outside_browser
        self._logger = logging.getLogger(__name__)

    def __str__(self):
        return 'Daily Puzzle'

    def run(self):
        d = self._account.get('community/index.phtml')
        d.addCallback(self._on_page)
        return d

    def _on_page(self, page):
        form = page.find('form', attrs=self._POLL_FORM_ATTRS)
        if not form:
            self._logger.info('Puzzle is not available')
            return

        d = self._outside_browser.get(
            'http://www.jellyneo.net/?go=dailypuzzle')
        d.addCallback(self._on_answers_page)
        return d

    def _on_answers_page(self, page):
        page = BeautifulSoup(page)
        daily_answer = page.find(text=self._ANSWER_DATE_RE)
        if not daily_answer:
            raise PageParseError(page)

        answer_date = datetime.datetime.strptime(
            daily_answer.nextSibling.text,
            '%A, %B %d, %Y').date()

        if answer_date != datetime.date.today():
            raise NoAnswerError()

        answer = page.find(
            style='font-size:15px; font-weight:bold; color:blue').text

        return self._submit_answer(answer)

    def _submit_answer(self, answer):
        d = self._account.get('community/index.phtml')
        d.addCallback(self._on_submission_page, answer)
        return d

    def _on_submission_page(self, page, answer):
        option = page.find('option', text=answer)
        if not option:
            raise PageParseError(page)

        option = option.parent
        for key, value in option.attrs:
            if key == 'value':
                answer_value = value
                break
        else:
            raise PageParseError(page)

        data = dict(
            trivia_date=datetime.date.today().strftime('%Y-%m-%d'),
            trivia_response=answer_value)

        d = self._account.post('/community/index.phtml', data=data)
        d.addCallback(self._on_post_answer)
        return d

    def _on_post_answer(self, page):
        award_string = page.find(text=self._AWARD_RE)
        if not award_string:
            raise PageParseError(page)

        np = award_string.nextSibling.text
        self._logger.info('Won %s', np)
