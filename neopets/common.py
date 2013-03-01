class NoNpInPage(Exception):
    pass


class PageParseError(Exception):
    def __init__(self, page):
        super(PageParseError, self).__init__()
        self.page = page


class Event(object):
    def __init__(self):
        self._callbacks = set()

    def register(self, callback):
        self._callbacks.add(callback)

    def unregister(self, callback):
        self._callbacks.remove(callback)

    def call(self, *args, **kwargs):
        for callback in self._callbacks:
            callback(*args, **kwargs)


def get_np(page):
    a = page.find('a', id='npanchor')
    if not a:
        raise NoNpInPage()
    return int(a.text.replace(',', ''))
