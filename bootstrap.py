#! /usr/bin/env python

import site
site.addsitedir('.')

from monteur.setup import BootstrapCommand
command = BootstrapCommand()
command()
