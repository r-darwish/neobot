import os
from collections import namedtuple
from ConfigParser import SafeConfigParser

Account = namedtuple('Account', ('username', 'password'))
Misc = namedtuple('Misc', ('data_dir', 'page_archiver'))
Logging = namedtuple('Logging', ('console_level', 'file_level'))


class ConfigurationError(Exception):
    def __init__(self, filename):
        super(ConfigurationError, self).__init__(
            'Bad configuration file: %s' % (filename, ))


class Config(object):
    def __init__(self, account, misc, logging):
        self._account = account
        self._misc = misc
        self._logging = logging

    @property
    def account(self):
        return self._account

    @property
    def misc(self):
        return self._misc

    @property
    def logging(self):
        return self._logging

    @classmethod
    def load_from_ini_file(cls, filename):
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

        return cls(account, misc, logging)
