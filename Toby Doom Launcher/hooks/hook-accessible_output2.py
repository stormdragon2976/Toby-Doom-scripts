#!/usr/bin/env python3

import os.path
import accessible_output2 as ao2

_dir = os.path.dirname(ao2.__file__)
binaries = [(os.path.join(_dir, 'lib'), os.path.join('accessible_output2', 'lib'))]
