import os
from collections import namedtuple
from sqlalchemy import create_engine, Table, Column, Integer, String, MetaData, DateTime


Database = namedtuple('Database', ('engine', 'tables'))
Tables = namedtuple('Tables', ('pages'))


metadata = MetaData()


pages = Table(
    'pages', metadata,
    Column('page_id', Integer, primary_key=True, nullable=False),
    Column('time', DateTime, nullable=False),
    Column('url', String(1024), nullable=False),
    Column('data', String(1024), nullable=True),
    Column('referer', String(1024), nullable=True))


def get_engine(data_directory, echo=False):
    engine = create_engine('sqlite:///%s' % (
        os.path.join(data_directory, 'neopets.db')), echo=echo)
    with engine.connect():
        metadata.create_all(engine)

    return Database(engine, Tables(pages))
