#!/usr/bin/env python

import argparse

from .anchor import main


# argparse
parser = argparse.ArgumentParser(description="Configure and execute the anchor daemon.")
parser.add_argument("-b", "--rf-bw", type=int, default=int(56e6), help="RF bandwidth")
parser.add_argument("-f", "--cntr-freq", type=long, default=long(2.462e9), help="center frequency")
parser.add_argument("-r", "--samp-rate", type=int, default=int(50e6), help="sampling rate")
parser.add_argument("-l", "--buff-len", type=int, default=int(2**18), help="libiio buffer length")

# parse arguments
args = parser.parse_args()

main(args)
