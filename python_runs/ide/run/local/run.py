#!/usr/bin/env python3
import os, sys, subprocess

RUNNER = "/home/computron/Documents/pythonTools/modules/src/modules/abstract_ide/run_ide_local.py"
PYTHONPATH_ROOT = "/home/computron/Documents/pythonTools/modules/src"

def main():
    env = os.environ.copy()
    env["PYTHONPATH"] = PYTHONPATH_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    # Optional: if Wayland causes issues with Qt, force XCB:
    # env["QT_QPA_PLATFORM"] = "xcb"
    subprocess.run([sys.executable, RUNNER], env=env, check=True)

if __name__ == "__main__":
    main()
