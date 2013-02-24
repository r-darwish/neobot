class NoNpInPage(Exception):
    pass

class PageParseError(Exception):
    def __init__(self, page):
        super(PageParseError, self).__init__()
        self.page = page


def get_np(page):
    a = page.find('a', id='npanchor')
    if not a:
        raise NoNpInPage()
    return int(a.text.replace(',', ''))
