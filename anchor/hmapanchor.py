"""
hmapanchor.py: Orion heatmap system anchor code.
"""

import logging
import multiprocessing
import socket
import timeit

import numpy as np

from .core import FMCOMMS5


# host PC communication
COMM_PORT = 2206

# FMCOMMS5 buffer size (in samples)
BUFF_LENGTH = 2**16

# if True, logs statustics
DEBUG = True


# logging
LOG_FORMAT = "%(filename)s:%(funcName)s:%(asctime)s -- %(message)s"
logging.basicConfig(format=LOG_FORMAT, datefmt="%H:%M:%S", level=logging.INFO)


class AcquireProcess(multiprocessing.Process):

    def __init__(self, quit_evt, bandwidth, samp_rate, center_freq):

        super(AcquireProcess, self).__init__()

        # set process data
        self.quit_evt = quit_evt

        # create FMCOMMS5 device
        self.fmcomms5 = FMCOMMS5(bandwidth, samp_rate, center_freq, BUFF_LENGTH)

        # create holder for sample data
        self.data_queue = multiprocessing.Queue(maxsize=128)

    def run(self):

        iter_num = 0
        n_pkts = 0
        has_oflow = False

        start = timeit.default_timer()
        while not self.quit_evt.is_set():
            iter_num += 1

            # check buffers before copying data out of memory
            self.fmcomms5.refill_buffer()
            if self.fmcomms5.check_buffer():
                n_pkts += 1
                data = self.fmcomms5.read_buffer()
                self.data_queue.put(data)

            # check for overflow
            if DEBUG and not has_oflow and self.fmcomms5.check_overflow():
                has_oflow = True
                logging.info("Iteration {0}: overflow occurred".format(iter_num))

            # log status messages
            if DEBUG and iter_num % 65536 == 0:
                runtime = (timeit.default_timer() - start) / iter_num * 1000
                message = "{0:.5f}ms runtime; {1} packets".format(runtime, n_pkts)
                logging.info("Iteration {0}: {1}".format(iter_num, message))

        # cleanup
        self.data_queue.close()
        self.data_queue.join_thread()

    def get_data_queue(self):

        return self.data_queue


class SendProcess(multiprocessing.Process):

    def __init__(self, quit_evt, data_queue):

        super(SendProcess, self).__init__()

        # set process data
        self.quit_evt = quit_evt
        self.data_queue = data_queue

        # create socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", COMM_PORT))

    def run(self):

        # continuously read from the 
        while not self.quit_evt.is_set():
            data = self.data_queue.get()

            #TODO: use TCP/IP protocol here instead?
            for n in range(0, len(data), pkt_size):
                sock.sendto(data[n:n+pkt_size], (host_addr, COMM_PORT))
            sock.sendto("end", (host_addr, COMM_PORT))

        # after the quit event has been triggered, flush the queue
        while not self.data_queue.empty():
            self.data_queue.get()


def main(args):

    # set arguments
    bandwidth = args.bandwidth
    samp_rate = args.samp_rate
    center_freq = args.center_freq

    # create reader and communicator processes
    quit_evt = multiprocessing.Event()
    acq_proc = AcquireProcess(quit_evt, bandwidth, samp_rate, center_freq)
    send_proc = SendProcess(quit_evt, acq_proc.get_data_queue())

    # start processes
    acq_proc.start()
    send_proc.start()


if __name__ == "__main__":

    # call main function
    main(parser.parse_args())

