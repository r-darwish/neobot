import datetime
import logging
import os
import sqlite3

class PageArchiver(object):
    def __init__(self, archive_dir):
        self._logger = logging.getLogger(__name__)
        self._archive_dir = archive_dir
        self._db = sqlite3.connect(
            os.path.join(
                self._archive_dir,
                'archive.db'))
        self._init_db()

    def _init_db(self):
        cur = self._db.execute(
            'SELECT name FROM sqlite_master WHERE name = \'pages\'')
        if cur.fetchone():
            return

        self._db.execute(
            'CREATE TABLE pages (page_id INTEGER PRIMARY KEY AUTOINCREMENT, '
            'time DATETIME, url TEXT, data TEXT, referer TEXT)')
        self._db.commit()

    def archive(self, page, url, data, referer):
        self._db.execute(
            'INSERT INTO pages (time, url, data, referer) '
            'VALUES (?, ?, ?, ?)',
            (datetime.datetime.now(), url.geturl(), str(data), referer))

        cur = self._db.execute(
            'SELECT last_insert_rowid()')

        page_id,  = cur.fetchone()
        page_path = os.path.join(
            self._archive_dir,
            '%d.html' % (page_id, ))

        with open(page_path, 'w') as p:
            p.write(str(page))

        self._db.commit()
