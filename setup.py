#!/usr/bin/env python

from distutils.core import setup


setup(name="fmcomms5-anchor",
      version="1.1",
      description="Orion anchor daemon.",
      author="Orion Innovations",
      packages=["anchor", "anchor.core", "anchor.comms"],
      package_data={"anchor.comms": ["libsocket_ext.so"]}
     )
