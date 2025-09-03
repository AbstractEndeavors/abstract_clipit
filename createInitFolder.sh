#!/bin/bash

# Check if name parameter is provided
if [ -z "$1" ]; then
    echo "Error: Please provide a module name"
    exit 1
fi

NAME=$1

# Create directory and navigate into it
mkdir "$NAME"
cd "$NAME"

# Create __init__.py with import statement
echo "from .$NAME import *" > __init__.py

# Create $NAME.py and paste clipboard content
# Using xclip for Linux systems; for macOS, replace 'xclip -selection clipboard' with 'pbpaste'
xclip -selection clipboard -o > "$NAME.py"

# Open files in nano for editing
nano __init__.py
nano "$NAME.py"
