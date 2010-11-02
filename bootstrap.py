#! /usr/bin/env python

import os
import sys

zeam_src = os.path.join(os.getcwd(), 'src')
sys.path[0:0] = [zeam_src,]

from zeam.setup.base.setup import BootstrapCommand
BootstrapCommand().run()
