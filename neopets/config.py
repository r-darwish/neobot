import os
from collections import namedtuple
from ConfigParser import SafeConfigParser

Account = namedtuple('Account', ('username', 'password'))
Misc = namedtuple('Misc', ('data_dir', 'page_archiver'))
Logging = namedtuple('Logging', ('console_level', 'file_level'))
Application = namedtuple('Application', ('dailies', 'restockers',
                                         'restocker_refresh_interval'))
Sniper = namedtuple(
    'Sniper',
    ('refresh_interval', 'auctions_to_analyze', 'bargain_threshold', 'profit_threshold',
     'interesting_keywords', 'bad_keywords', 'minimum_np_for_playing', 'minimal_auction_number',
     'item_samples', 'item_price_max_deviation', 'suspecious_yield_threshold'))
Config = namedtuple('Config', ('account', 'misc', 'logging', 'application', 'sniper'))

class ConfigurationError(Exception):
    def __init__(self, filename):
        super(ConfigurationError, self).__init__(
            'Bad configuration file: %s' % (filename, ))

def load_from_ini_file(filename):
    cp = SafeConfigParser()
    files_read = cp.read([filename, ])
    if filename not in files_read:
        raise ConfigurationError(filename)

    account = Account(
        cp.get('account', 'username'),
        cp.get('account', 'password'))

    misc = Misc(
        os.path.expandvars(cp.get('misc', 'data_dir')),
        cp.getboolean('misc', 'page_archiver'))

    logging = Logging(
        cp.get('logging', 'console_level'),
        cp.get('logging', 'file_level'))

    sniper = Sniper(
        cp.getint('sniper', 'refresh_interval'),
        cp.getint('sniper', 'auctions_to_analyze'),
        cp.getint('sniper', 'bargain_threshold'),
        cp.getint('sniper', 'profit_threshold'),
        frozenset(cp.get('sniper', 'interesting_keywords').split(',')),
        frozenset(cp.get('sniper', 'bad_keywords').split(',')),
        cp.getint('sniper', 'minimum_np_for_playing'),
        cp.getint('sniper', 'minimal_auction_number'),
        cp.getint('sniper', 'item_samples'),
        cp.getfloat('sniper', 'item_price_max_deviation'),
        cp.getfloat('sniper', 'suspecious_yield_threshold'),)

    application = Application(
        cp.getboolean('application', 'dailies'),
        cp.get('application', 'restockers').split(','),
        cp.getint('application', 'restocker_refresh_interval'))

    return Config(account, misc, logging, application, sniper)
