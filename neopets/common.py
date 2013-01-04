class PageParseError(Exception):
    def __init__(self, page):
        super(PageParseError, self).__init__()
        self.page = page


def get_np(page):
    return int(page.find('a', id='npanchor').text.replace(',', ''))
