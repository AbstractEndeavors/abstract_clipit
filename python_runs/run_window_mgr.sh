#!/bin/bash
# Wrapper to call the Python script in the current directory

# Get the directory where the command is invoked
CURRENT_DIR=$(pwd)

# Call the Python script with the current directory as the working directory
python3 /home/computron/bashScripts/python/python_runs/get_window_mgr.py
