"""
fmcomms5.py: FMCOMMS5 helper functions.
"""

import ctypes
import os
import time

import iio
import numpy as np


# AD9361 C library
libad9361 = ctypes.CDLL("libad9361.so")
libad9361.ad9361_fmcomms5_multichip_sync.argtypes = [ctypes.c_void_p,
                                                     ctypes.c_uint]
libad9361.ad9361_fmcomms5_multichip_sync.restype = ctypes.c_int
libad9361.ad9361_fmcomms5_phase_sync.argtypes = [ctypes.c_void_p,
                                                 ctypes.c_longlong]
libad9361.ad9361_fmcomms5_phase_sync.restype = ctypes.c_int

# pointer to memory location with int16 values
c_int16_p = ctypes.POINTER(ctypes.c_int16)

# gain control mode
RX_GAIN_MODE = "manual"

# hardware gain value (in dB)
RX_GAIN_VALUE = 32
TX_GAIN_VALUE = -20

# minimum value such that signal exists (either I or Q, not abs)
MIN_SIGNAL_VALUE = 32


class FMCOMMS5(object):

    def __init__(self):

        # create local IIO context
        self.iio_ctx = iio.Context()

        # access physical devices
        self.dev_a = self.iio_ctx.find_device("ad9361-phy")
        self.dev_b = self.iio_ctx.find_device("ad9361-phy-B")
        self.devs = (self.dev_a, self.dev_b)

        self.data = None

    def configure_rx(self, bw, rate):

        for dev in self.devs:

            # configure RX channels
            for idx in range(2):

                # for RX, do not use output
                chan = dev.find_channel("voltage" + str(idx), False)

                # set gain parameters
                chan.attrs["gain_control_mode"].value = RX_GAIN_MODE
                chan.attrs["hardwaregain"].value = str(RX_GAIN_VALUE)

                # set chip attributes (valid only for 0th channel)
                if idx == 0:

                    # set bw and sampling frequency
                    chan.attrs["rf_bandwidth"].value = str(bw)
                    chan.attrs["sampling_frequency"].value = str(rate)

                    # set DC tracking parameters
                    chan.attrs["bb_dc_offset_tracking_en"].value = str(1)
                    chan.attrs["rf_dc_offset_tracking_en"].value = str(1)
                    chan.attrs["quadrature_tracking_en"].value = str(1) 

    def configure_tx(self, bw, rate):

        for dev in self.devs:

            # configure TX channels
            for idx in range(2):
                chan = dev.find_channel("voltage" + str(idx), True)

                # set hardware gain
                chan.attrs["hardwaregain"].value = str(TX_GAIN_VALUE)

                # set chip attributes
                if idx == 0:

                    # set bw and sampling frequency
                    chan.attrs["rf_bandwidth"].value = str(bw)
                    chan.attrs["sampling_frequency"].value = str(rate)

    def set_rx_port(self, port):

        for dev in self.devs:
            chan = dev.find_channel("voltage0", False)
            chan.attrs["rf_port_select"].value = port

    def set_tx_port(self, port):

        for dev in self.devs:
            chan = dev.find_channel("voltage0", True)
            chan.attrs["rf_port_select"].value = port

    def set_rx_lo_freq(self, freq):

        for dev in self.devs:
            chan_rxlo = dev.find_channel("altvoltage0", True)
            chan_rxlo.attrs["frequency"].value = str(freq)

    def set_tx_lo_freq(self, freq):

        for dev in self.devs:
            chan_txlo = dev.find_channel("altvoltage1", True)
            chan_txlo.attrs["frequency"].value = str(freq)

    def synchronize_devices(self):

        # directly call C library for multichip sychronization
        return libad9361.ad9361_fmcomms5_multichip_sync(self.iio_ctx._context, 3)

    def synchronize_phases(self, freq):

        # directly call C library for phase synchronization
        return libad9361.ad9361_fmcomms5_phase_sync(self.iio_ctx._context, freq)

    def create_streams(self, blen):

        self.dev_rx = self.iio_ctx.find_device("cf-ad9361-A")

        # configure master streaming devices
        for n in range(8):
            chan = self.dev_rx.find_channel("voltage" + str(n))
            chan.enabled = True

        # create IIO buffer object
        self.buf_rx = iio.Buffer(self.dev_rx, blen)

    def check_overflow(self):

        return (self.dev_rx.reg_read(0x80000088) & 4 > 0)

    def refill_buffer(self):

        # buffer size is always constant
        self.buf_rx.refill()
        self.data = self.buf_rx.read()

    def get_buffer_data(self):

        # return previously acquired data from refill_buffer()
        return self.data

    def check_buffer(self):

        #if self.check_overflow():
        #    print("Overflow detected")

        # without copying memory, check the "RSSI" of the buffer
        #blen = self.buf_rx._samples_count
        #ptr = ctypes.cast(self.get_buffer_ptr(), c_int16_p)
        #arr = np.ctypeslib.as_array(ptr, shape=(blen, 8))
        arr = np.frombuffer(self.data, dtype=np.int16)
        arr = arr.reshape((-1, 8))

        # simple threshold operator
        return np.any(arr[::64,0] > MIN_SIGNAL_VALUE)


