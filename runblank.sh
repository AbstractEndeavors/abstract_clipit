#!/bin/bash

# Create the directory if it doesn't exist
mkdir -p /home/computron/tempPy

# Define the path for the Python file
TEMP_FILE="/home/computron/tempPy/blankrun.py"

# Create or overwrite the file with a simple template
echo "# Test your Python functions here" > $TEMP_FILE

# Open the specified Python file in IDLE
idle $TEMP_FILE &
