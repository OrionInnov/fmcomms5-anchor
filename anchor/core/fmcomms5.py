"""
fmcomms5.py: FMCOMMS5 helper functions.
"""

import ctypes
import time

import iio
import numpy as np


# operational mode
ENSM_MODE = "rx"

# port selection
RX_PORT_SELECT = "B_BALANCED"

# gain control mode
GAIN_CONTROL_MODE = "manual"

# hardware gain value (in dB)
RX_GAIN_VALUE = 30

# minimum value such that signal exists (either I or Q, not abs)
MIN_SIGNAL_VALUE = 64


class FMCOMMS5(object):

    def __init__(self, bandwidth, samp_rate, cntr_freq, buff_size):

        # create local IIO context
        self.context = iio.Context()

        # configure the AD9361 devices
        self._configure_ad9361_phy(bandwidth, samp_rate, cntr_freq)
        self._synchronize_devices(fix_timing=True)
        self._create_streams(buff_size)

    def _configure_ad9361_phy(self, bandwidth, samp_rate, cntr_freq):

        # access physical devices
        self.device_a = self.context.find_device("ad9361-phy")
        self.device_b = self.context.find_device("ad9361-phy-B")

        # set mode to RX only
        self.device_a.attrs["ensm_mode"].value = ENSM_MODE
        self.device_b.attrs["ensm_mode"].value = ENSM_MODE

        # configure physical devices
        for dev in (self.device_a, self.device_b):

            # setting a small number of buffers ensures that the "next"
            # batch is as fresh as possible
            #dev.set_kernel_buffers_count(2)

            # configure RX channels
            for idx in range(2):

                # LO channel is always output
                chan = dev.find_channel("voltage" + str(idx), False)

                # set gain parameters
                chan.attrs["gain_control_mode"].value = GAIN_CONTROL_MODE
                chan.attrs["hardwaregain"].value = str(RX_GAIN_VALUE)

                # set chip attributes (valid only for 0th channel)
                if idx == 0:

                    # set bandwidth and sampling frequency
                    chan.attrs["rf_port_select"].value = RX_PORT_SELECT
                    chan.attrs["rf_bandwidth"].value = str(bandwidth)
                    chan.attrs["sampling_frequency"].value = str(samp_rate)

                    # set DC tracking parameters
                    chan.attrs["bb_dc_offset_tracking_en"].value = str(1)
                    chan.attrs["rf_dc_offset_tracking_en"].value = str(1)
                    chan.attrs["quadrature_tracking_en"].value = str(0)

                # DEBUG: gain value must be set again (for some reason)
                chan.attrs["hardwaregain"].value = str(RX_GAIN_VALUE)

            # set LO channel attributes
            chan_lo = dev.find_channel("altvoltage0", True)
            chan_lo.attrs["frequency"].value = str(cntr_freq)

    def _synchronize_devices(self, fix_timing=False):

        # fixup interface timing (buggy?)
        if fix_timing:
            self.device_b.reg_write(0x6, self.device_a.reg_read(0x6))
            self.device_b.reg_write(0x7, self.device_a.reg_read(0x7))

        # set "ensm_mode" flags
        ensm_mode_a = self.device_a.attrs["ensm_mode"].value
        ensm_mode_b = self.device_b.attrs["ensm_mode"].value
        self.device_a.attrs["ensm_mode"].value = "alert"
        self.device_b.attrs["ensm_mode"].value = "alert"

        # copied from libad9361-iio/ad9361_multichip_sync.c
        for n in range(6):
            self.device_b.attrs["multichip_sync"].value = str(n)
            self.device_a.attrs["multichip_sync"].value = str(n)

        # allow sync to propagate
        time.sleep(1)

        # set "ensm_mode" flags
        self.device_a.attrs["ensm_mode"].value = ensm_mode_a
        self.device_b.attrs["ensm_mode"].value = ensm_mode_b

    def _create_streams(self, buff_size):

        self.device_rx = self.context.find_device("cf-ad9361-A")

        # configure master streaming devices
        for n in range(8):
            chan = self.device_rx.find_channel("voltage" + str(n))
            chan.enabled = True

        # create buffer (4 channels x 2 elements x 2 bytes)
        self.buffer_rx = iio.Buffer(self.device_rx, buff_size)
        self.buf_type = ctypes.c_byte * buff_size * 4 * 2 * 2

    def check_overflow(self):

        return self.device_rx.reg_read(ctypes.c_uint32(0x80000088)) & 4

    def refill_buffer(self):

        self.buffer_rx.refill()

    def check_buffer(self):

        # hacky way to directly read from buffer
        start = iio._buffer_start(self.buffer_rx._buffer)
        buf_arr = self.buf_type.from_address(start)

        # load memory directly
        samps = np.frombuffer(buf_arr, np.int16)
        max_val = np.abs(samps[::256]).max()

        return max_val > MIN_SIGNAL_VALUE

    def read_buffer(self):

        return self.buffer_rx.read()
