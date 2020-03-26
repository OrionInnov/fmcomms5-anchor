#!/usr/bin/env python

import argparse

from .comms import socket_ext
from .core import FMCOMMS5


# local data port
DATA_PORT = 9133


# argparse
parser = argparse.ArgumentParser(description="Configure and execute the anchor daemon.")
parser.add_argument("-b", "--bw", type=int, default=int(2e6), help="RF bandwidth")
parser.add_argument("-f", "--freq", type=long, default=long(915e6), help="center frequency")
parser.add_argument("-r", "--rate", type=int, default=int(5e6), help="sampling rate")
parser.add_argument("-l", "--blen", type=int, default=int(), help="buffer length in samples")
parser.add_argument("-a", "--addr", type=str, default="192.168.100.100", help="server IP address")
parser.add_argument("-p", "--port", type=int, default=9133, help="server port")

# parse arguments
args = parser.parse_args()


def main(args):

    (addr, port) = (args.addr, args.port)

    # create FMCOMMS5 device
    fmcomms5 = FMCOMMS5(args.bw, args.rate, args.freq, args.blen)

    # open socket
    sock = socket_ext.socket_udp("0.0.0.0", DATA_PORT)

    # continuously read from FMCOMMS5
    while True:
        sz = fmcomms5.refill_buffer()

        # check_buffer() ensures that signal received is above the noise floor
        if fmcomms5.check_buffer():
            ptr = fmcomms5.get_buffer_ptr()
            socket_ext.sendto_all(sock, ptr, sz, addr, port)


main(args)
