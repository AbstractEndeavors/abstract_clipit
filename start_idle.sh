#!/bin/bash

# Setup Conda environment
# Setup Conda environment
export PATH="/home/computron/miniconda/bin"
source activate base

# Define Python executable path from the activated environment
PYTHON_PATH=$(which python)

# Check if a script path was provided as an argument
if [ $# -gt 0 ]; then
    SCRIPT_PATH=$1
    # Start IDLE using the specific Python executable and open the specified Python script
    $PYTHON_PATH -m idlelib.idle "$SCRIPT_PATH"
else
    # Start IDLE normally using the specific Python executable
    $PYTHON_PATH -m idlelib.idle
fi
