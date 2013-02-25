import datetime
import logging
import os

class PageArchiver(object):
    def __init__(self, archive_dir, db):
        self._logger = logging.getLogger(__name__)
        self._archive_dir = archive_dir
        self._db = db

    def archive(self, page, url, data, referer):
        query = self._db.tables.pages.insert().values(
            time=datetime.datetime.now(), url=url, data=data,
            referer=referer)

        with self._db.engine.connect() as conn:
            result = conn.execute(query)
            page_id = result.last_inserted_ids()[0]

        page_path = os.path.join(
            self._archive_dir,
            '%08d.html' % (page_id, ))

        with open(page_path, 'w') as p:
            p.write(str(page))
