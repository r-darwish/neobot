import os
from collections import namedtuple
from ConfigParser import SafeConfigParser

Account = namedtuple('Account', ('username', 'password'))
Misc = namedtuple('Misc', ('data_dir', 'page_archiver'))
Logging = namedtuple('Logging', ('console_level', 'file_level'))
Application = namedtuple('Application', ('dailies', 'restockers',
                                         'restocker_refresh_interval'))

Config = namedtuple('Config', ('account', 'misc', 'logging', 'application'))

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

    application = Application(
        cp.getboolean('application', 'dailies'),
        cp.get('application', 'restockers').split(','),
        cp.getint('application', 'restocker_refresh_interval'))

    return Config(account, misc, logging, application)
