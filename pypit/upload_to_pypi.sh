#!/bin/bash
# Wrapper to call the Python script in the current directory

# Get the directory where the command is invoked
CURRENT_DIR=$(pwd)

# Call the Python script with the current directory as the working directory
#python3 /home/flerb/Documents/bashScripts/python/pypit.py
python3 "/home/op/bashScripts/python/pypit/main.py"
