"""
fmcomms5.py: FMCOMMS5 helper functions.
"""

import ctypes
import time

import iio
import numpy as np

libad9361 = ctypes.CDLL("libad9361.so")


# operational mode
ENSM_MODE = "rx"

# port selection
RX_PORT_SELECT = "B_BALANCED"

# gain control mode
GAIN_CONTROL_MODE = "manual"

# hardware gain value (in dB)
RX_GAIN_VALUE = 30

# minimum value such that signal exists (either I or Q, not abs)
MIN_SIGNAL_VALUE = 8


class FMCOMMS5(object):

    def __init__(self, bw, rate, freq, blen):

        # create local IIO context
        self.iio_ctx = iio.Context()

        # configure the AD9361 devices
        self._configure_ad9361_phy(bw, rate, freq)
        self._synchronize_phases(freq)
        self._create_streams(blen)

    def _configure_ad9361_phy(self, bw, rate, freq):

        # access physical devices
        self.dev_a = self.iio_ctx.find_device("ad9361-phy")
        self.dev_b = self.iio_ctx.find_device("ad9361-phy-B")

        # set mode to RX only
        self.dev_a.attrs["ensm_mode"].value = ENSM_MODE
        self.dev_b.attrs["ensm_mode"].value = ENSM_MODE

        # configure physical devices
        for dev in (self.dev_a, self.dev_b):

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

                    # set bw and sampling frequency
                    chan.attrs["rf_port_select"].value = RX_PORT_SELECT
                    chan.attrs["rf_bandwidth"].value = str(bw)
                    chan.attrs["sampling_frequency"].value = str(rate)

                    # set DC tracking parameters
                    chan.attrs["bb_dc_offset_tracking_en"].value = str(1)
                    chan.attrs["rf_dc_offset_tracking_en"].value = str(1)
                    chan.attrs["quadrature_tracking_en"].value = str(0)

                # TODO: gain value must be set again (for some reason)
                chan.attrs["hardwaregain"].value = str(RX_GAIN_VALUE)

            # set LO channel attributes
            chan_lo = dev.find_channel("altvoltage0", True)
            chan_lo.attrs["frequency"].value = str(freq)

    def _synchronize_devices(self):

        master = self.dev_a._device
        slaves = ctypes.pointer(self.dev_a._device)
        libad9361.ad9361_multichip_sync(master, slaves, 1, 3)

    def _synchronize_phases(self, freq):

        libad9361.ad9361_fmcomms5_phase_sync(self.iio_ctx._context, freq)

    def _create_streams(self, blen):

        self.device_rx = self.iio_ctx.find_device("cf-ad9361-A")

        # configure master streaming devices
        for n in range(8):
            chan = self.device_rx.find_channel("voltage" + str(n))
            chan.enabled = True

        # create IIO buffer object
        self.buf_rx = iio.Buffer(self.device_rx, blen)
        self.sz_buf = blen * 4 * 2 * 2

    def check_overflow(self):

        return self.device_rx.reg_read(ctypes.c_uint32(0x80000088)) & 4

    def refill_buffer(self):

        # buffer size is always constant
        self.buf_rx.refill()
        return self.sz_buf

    def get_buffer_ptr(self):

        # it is the user's responsibility to copy the return value to a new
        # array if modifications are made outside of the FMCOMMS5 object
        return iio._buffer_start(self.buf_rx._buffer)

    def check_buffer(self):

        # without copying memory, check the RSSI of the existing buffer
        ptr = self.get_buffer_ptr()
        arr = numpy.ctypeslib.as_array(ptr, shape=(1, self.sz_buf))
        arr = arr.view(np.int16).reshape((8, -1))

        # read data from channel 0
        mag0 = np.linalg.norm(arr[:2,:], axis=0)
        return np.any(mag0 > MIN_SIGNAL_VALUE)


