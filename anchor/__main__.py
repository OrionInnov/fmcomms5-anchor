#!/usr/bin/env python

import argparse
import multiprocessing
import os
import Queue
import socket
import time

from .core import FMCOMMS5


# local data port
DATA_PORT = 9133


# argparse
parser = argparse.ArgumentParser(description="Configure and execute the anchor daemon.")
parser.add_argument("-b", "--bw", type=int, default=int(1.6e6), help="RF bandwidth")
parser.add_argument("-f", "--freq", type=int, default=int(915e6), help="center frequency")
parser.add_argument("-r", "--rate", type=int, default=int(2.5e6), help="sampling rate")
parser.add_argument("-l", "--blen", type=int, default=1000, help="buffer length in samples")
parser.add_argument("-a", "--addr", type=str, default="192.168.100.5", help="server IP address")
parser.add_argument("-p", "--port", type=int, default=9133, help="server port")

# parse arguments
args = parser.parse_args()




def xfer(stop, queue, addr, port):

    os.nice(19)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    while not stop.is_set():
        try:
            data = queue.get_nowait()
        except Queue.Empty:
            time.sleep(0.1)
            continue
        if len(data) == 0:
            print("Sent data batch")
        sock.sendto(data, (addr, port))


def main(args):

    # create FMCOMMS5 device
    fmcomms5 = FMCOMMS5()
    fmcomms5.configure_ad9361_rx(args.bw, args.rate)
    fmcomms5.synchronize_phases(args.freq)
    fmcomms5.create_streams(args.blen)
    print("FMCOMMS5 configuration complete")

    # open socket
    stop = multiprocessing.Event()
    queue = multiprocessing.Queue()
    xargs = (stop, queue, args.addr, args.port)
    xproc = multiprocessing.Process(target=xfer, args=xargs)
    xproc.start()
    print("Spawned network process")

    # continuously read from FMCOMMS5
    is_active = False
    while True:
        fmcomms5.refill_buffer()

        if fmcomms5.check_buffer():
            queue.put(fmcomms5.get_buffer_data())
            is_active = True
            continue

        if is_active:
            queue.put(bytes())

        is_active = False

    stop.set()


main(args)
