#!/usr/bin/env python

import argparse

from .taganchor import main as main_tag
from .hmapanchor import main as main_hmap


def main():

    # argparse
    parser = argparse.ArgumentParser(description="Configure and execute the anchor daemon.")
    parser.add_argument("-d", "--daemon", choices=["tag", "hmap"], help="daemon to execute")
    parser.add_argument("-b", "--bandwidth", type=int, default=int(44e6), help="bandwidth")
    parser.add_argument("-s", "--samp-rate", type=int, default=int(50e6), help="sample rate")
    parser.add_argument("-c", "--center-freq", type=long, default=long(2.462e9), help="center frequency")

    # parse arguments
    args = parser.parse_args()

    # call appropriate daemon
    if args.daemon == "tag":
        main_tag(args)
    else:
        main_hmap(args)


if __name__ == "__main__":
    main()
