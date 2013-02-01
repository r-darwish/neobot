#!/usr/bin/env python
import argparse
import logging
import sys
from BeautifulSoup import BeautifulSoup

parser = argparse.ArgumentParser(usage="%(prog)s [options] args...")
parser.add_argument("-v", action="append_const", const=1, dest="verbosity", default=[],
                    help="Be more verbose. Can be specified multiple times to increase verbosity further")
parser.add_argument("-p", "--page", required=True,
                    help="Page to parse")


def main(args):
    with open(args.page, 'r') as p:
        page = p.read()

    # Test code here
    from neopets.account import Account
    acc = Account('/tmp/data', None, None, None)
    acc._on_page(page)
    return 0


################################## Boilerplate ################################
def _configure_logging(args):
    verbosity_level = len(args.verbosity)
    if verbosity_level == 0:
        level = "WARNING"
    elif verbosity_level == 1:
        level = "INFO"
    else:
        level = "DEBUG"
    logging.basicConfig(
        stream=sys.stderr,
        level=level,
        format="%(asctime)s -- %(message)s"
        )


#### For use with entry_points/console_scripts
def main_entry_point():
    args = parser.parse_args()
    _configure_logging(args)
    sys.exit(main(args))


if __name__ == "__main__":
    main_entry_point()
