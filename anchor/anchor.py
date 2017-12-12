"""
taganchor.py: Orion tag system anchor.
"""

import multiprocessing
import Queue
import socket
import subprocess

from .core import FMCOMMS5


# host PC communication
CMD_PORT = 2206
DATA_PORT = 2207


# FMCOMMS5 buffer size (in samples)
MAX_PKT_SIZE = 2**16 - 1 - 8 - 20


class StreamProcess(multiprocessing.Process):

    def __init__(self, args, quit_evt, cmd_queue):

        super(StreamProcess, self).__init__()

        # set process data
        self.quit_evt = quit_evt
        self.cmd_queue = cmd_queue

        # create FMCOMMS5 device
        self.fmcomms5 = FMCOMMS5(args.rf_bw, args.samp_rate,
                                 args.cntr_freq, args.buff_len)

        # create socket
        self.data_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.data_sock.bind(("0.0.0.0", DATA_PORT))
        self.max_sz = MAX_PKT_SIZE

        # holder variables: host address and number of batches
        self.send_addr = None
        self.num_send = 0

    def run(self):

        # loop until stop event is called
        while not self.quit_evt.is_set():
            self.fmcomms5.refill_buffer()

            # send data, if necessary
            self.fetch_inst()
            if self.num_send > 0:
                data = self.fmcomms5.read_buffer()
                self.send_data(data)
                self.num_send -= 1

    def fetch_inst(self):

        # there may not be a new command
        try:
            cmd = self.cmd_queue.get_nowait()
        except Queue.Empty:
            return

        # host's data port is +10000 away from command port
        self.send_addr = (cmd[0][0], cmd[0][1] + 1000)
        self.num_send = cmd[1]

    def send_data(self, data):

        # send data in max-size packets
        for n in range(0, len(data), self.max_sz):
            end = n + self.max_sz
            self.data_sock.sendto(data[n:end], self.send_addr)

        # empty packet denotes end of sequence
        self.data_sock.sendto("", self.send_addr)


def command_daemon(cmd_queue, buff_len, samp_rate):

    # create the socket (max UDP packet size)
    cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cmd_sock.bind(("0.0.0.0", CMD_PORT))
    cmd_sock.settimeout(None)
    cmd_sock.listen(1)

    while True:
        (conn, addr) = cmd_sock.accept()

        while True:
            cmd = conn.recv(4)

            # reboot anchor
            if cmd == "boot":
                subprocess.call(["sudo", "reboot"])

            # ping back
            elif cmd == "ping":
                conn.send("ping")

            # check buffer length
            elif cmd == "blen":
                conn.send(str(buff_len))

            # check sample rate
            elif cmd == "rate":
                conn.send(str(samp_rate))

            # keep sending data
            elif cmd == "data":
                cmd_queue.put((addr, float("inf")))

            # stop sending data
            elif cmd == "stop":
                cmd_queue.put((addr, 0))

            # send specific number of batches
            elif cmd.isdigit():
                cmd_queue.put((addr, int(cmd)))

            # close the connection
            else:
                break


def main(args):

    # create reader and communicator processes
    quit_evt = multiprocessing.Event()
    cmd_queue = multiprocessing.Queue()
    send_proc = StreamProcess(args, quit_evt, cmd_queue)

    # begin processes and command daemon
    send_proc.start()
    command_daemon(cmd_queue, args.buff_len, args.samp_rate)

    # if daemon exits, automatically reboot anchor
    quit_evt.set()
    send_proc.join()
    subprocess.call(["sudo", "reboot"])
