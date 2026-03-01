###!/usr/bin/env python3
##from pathlib import Path
##import os, subprocess, sys
### Target script
##target = Path("/home/computron/Documents/pythonTools/modules/src/modules/abstract_ide/run_ide_local.py")
### (Optional) make sure the package root is on PYTHONPATH
###   /src/modules is the import root for "abstract_ide"
##pkg_root = Path("/home/computron/Documents/pythonTools/modules/src/modules")
##env = os.environ.copy()
##env["PYTHONPATH"] = (str(pkg_root) + os.pathsep + env.get("PYTHONPATH", ""))
### Use current interpreter (works in venvs too)
##python = sys.executable
### Run it with its folder as cwd (helps when it reads relative files)
##subprocess.run([python, str(target)], cwd=str(target.parent), env=env, check=True)
from abstract_windows import *
path = "/home/computron/Documents/pythonTools/modules/src/modules/abstract_ide/run_ide_local.py"
launch_python_conda_script(path,monitor_index = 0)

