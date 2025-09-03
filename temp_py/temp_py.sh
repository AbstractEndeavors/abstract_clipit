#!/bin/bash

FILE="/home/computron/bashScripts/python/temp_py.py"

if [ ! -f "$FILE" ]; then
    echo "#!/usr/bin/env python3" > "$FILE"
    echo "# temp_py.py created on $(date)" >> "$FILE"
    echo "Created $FILE"
else
    echo "$FILE already exists"
fi

/home/computron/open_with_conda.sh "$FILE"