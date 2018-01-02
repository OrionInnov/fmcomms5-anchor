
from ctypes import cdll
import os


_dir_path = os.path.dirname(os.path.realpath(__file__))
_ext_path = os.path.join(_dir_path, "libsocket_ext.so")

socket_ext = cdll.LoadLibrary(_ext_path)
