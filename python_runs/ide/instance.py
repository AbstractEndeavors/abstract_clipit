#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json

# Import from your module (make sure its parent dir is on PYTHONPATH)
from abstract_windows import launch_python_conda_script

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: instance.py /abs/path/to/script.py [monitor_index]", file=sys.stderr)
        return 2

    target = os.path.abspath(sys.argv[1])
    if not os.path.isfile(target):
        print(f"Error: '{target}' not found.", file=sys.stderr)
        return 2

    # Optional monitor index (0-based). If not provided, default to 1.
    mon_idx = 1
    if len(sys.argv) >= 3:
        try:
            mon_idx = int(sys.argv[2])
        except ValueError:
            # Ignore bad values silently; keep default
            pass

    # Allow env overrides without changing code
    env_name = os.environ.get("ENV_NAME", "base")
    conda_exe = os.environ.get("CONDA_EXE", "/home/computron/miniconda/bin/conda")
    display   = os.environ.get("DISPLAY", ":0")

    res = launch_python_conda_script(
        target,
        env_name=env_name,
        conda_exe=conda_exe,
        display=display,
        monitor_index=mon_idx,
    )
    print(json.dumps(res))
    # consider it success if we either launched or focused an existing window
    return 0 if res and isinstance(res, dict) else 1

if __name__ == "__main__":
    sys.exit(main())
