"""
misc.py: Miscellaneous FMCOMMS5 anchor helper functions.
"""

import socket


def get_ip_address():
	"""
		Gets the OS's primary/default IP address.
	"""

    # hacky method to get primary IP address
    # create UDP connection to random host and read out default IP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(("8.8.8.8", 80))

    return sock.getsockname()[0]
