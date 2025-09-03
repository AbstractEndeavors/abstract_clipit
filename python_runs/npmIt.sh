#!/bin/bash

# Get the directory from which the Bash script is called
SCRIPT_DIR="$(pwd)"

# Path to the Python script (adjust if it's not in the same directory)
PYTHON_SCRIPT="/home/computron/bashScripts/python/python_runs/npmIt.py"

# Check if the Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script $PYTHON_SCRIPT not found."
    exit 1
fi

# Check if package.json exists in the current directory
if [ ! -f "$SCRIPT_DIR/package.json" ]; then
    echo "Error: package.json not found in $SCRIPT_DIR."
    exit 1
fi

# Run the Python script
python3 "$PYTHON_SCRIPT"

# Check if the Python script executed successfully
if [ $? -ne 0 ]; then
    echo "Error: Python script failed."
    exit 1
fi
#cd /var/www/abstractendeavors/secure-files && yarn remove @putkoff/abstract-utilities && yarn add @putkoff/abstract-utilities && yarn remove @putkoff/abstract-logins && yarn add @putkoff/abstract-logins && yarn remove @putkoff/abstract-files && yarn add @putkoff/abstract-files

echo "Package version updated and published successfully."
