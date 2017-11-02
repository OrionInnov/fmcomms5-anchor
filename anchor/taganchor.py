"""
taganchor.py: Orion tag system anchor.
"""

import socket
import subprocess

import numpy as np

from .core import FMCOMMS5


# host PC communication
COMMS_PORT = 2206

# FMCOMMS5 buffer size (in samples)
BUFFER_LENGTH = 2**19


def main(args):

    bandwidth = args.bandwidth
    samp_rate = args.samp_rate
    center_freq = args.center_freq

    # create FMCOMMS5 object
    fmcomms5 = FMCOMMS5(bandwidth, samp_rate, center_freq, BUFFER_LENGTH)

    # create the socket (max UDP packet size)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", COMMS_PORT))
    pkt_size = 2**16 - 1 - 8 - 20

    # acquire and send loop
    while True:

        # acquire data
        fmcomms5.refill_buffer()
        data = fmcomms5.read_buffer()

        # receive command from host PC
        (cmd, conn) = sock.recvfrom(4)
        (host_addr, _) = conn

        # shutdown anchor
        if cmd == "halt":
            subprocess.call(["sudo", "poweroff"])

        # reboot anchor
        elif cmd == "boot":
            subprocess.call(["sudo", "reboot"])

        # ping back
        elif cmd == "ping":
            sock.sendto("ping", (host_addr, COMMS_PORT))

        # check buffer length
        elif cmd == "blen":
            sock.sendto(str(BUFFER_LENGTH), (host_addr, COMMS_PORT))

        # check sample rate
        elif cmd == "rate":
            sock.sendto(str(samp_rate), (host_addr, COMMS_PORT))

        # send data
        elif cmd == "data":
            for n in range(0, len(data), pkt_size):
                end = n + pkt_size
                sock.sendto(data[n:end], (host_addr, COMMS_PORT))
            sock.sendto("", (host_addr, COMMS_PORT))

        # invalid command
        else:
            continue

