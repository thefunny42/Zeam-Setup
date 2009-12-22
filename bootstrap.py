#! /usr/bin/env python

import os
import sys

zeam_src = os.path.join(os.getcwd(), 'src')
sys.path[0:0] = [zeam_src,]

import zeam.setup.base.setup
zeam.setup.base.setup.setup()

