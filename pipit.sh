#!/bin/bash

# Define the pipinst function


# Path to the virtual environment
#VENV_PATH="/home/gamook/Documents/pythonScripts/virtual_env"

# Path to the requirements.txt file
#REQ_PATH="/home/gamook/Documents/pythonScripts/requirements.txt"

# Activate the virtual environment
#source "$VENV_PATH/bin/activate"
export PATH="/home/computron/miniconda/bin:$PATH"
source /home/computron/miniconda/etc/profile.d/conda.sh
conda activate base

# Check if at least one argument is given
if [ $# -eq 0 ]; then
    echo "Usage: $0 [pip options] <package1> [package2] [...]"
    exit 1
fi

# Install packages using pip with the provided arguments
if pip install "$@"; then
    # For each actual package argument (ignoring options)
    for arg in "$@"; do
        # Skip if the argument starts with a dash (it's an option)
        if [[ $arg != -* ]]; then
            # Extract the installed package version using pip freeze
            pkg_version=$(pip3 freeze | grep -i ^$arg==)
            # Append the package and its version to requirements.txt if not already listed
            if [ -n "$pkg_version" ] && ! grep -Fxq "$pkg_version" $REQ_PATH; then
                echo "$pkg_version" >> $REQ_PATH
            fi
        fi
    done
else
    echo "Installation failed"
    exit 1
fi

deactivate
