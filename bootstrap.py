#! /usr/bin/env python

import site
site.addsitedir('.')

from zeam.setup.base.setup import BootstrapCommand
command = BootstrapCommand()
command()
