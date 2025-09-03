#!/bin/bash

# Path to the virtual environment
VENV_PATH="/home/computron/miniconda"

# Activate the virtual environment
source "$VENV_PATH/bin/activate"

# Save the current directory as the project directory
PROJECT_DIR=$(pwd)
echo "$PROJECT_DIR"

# Navigate to the project directory
cd "$PROJECT_DIR"

# Ensure pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo "pyproject.toml not found. Creating pyproject.toml..."
    cat <<EOL > pyproject.toml
[build-system]
requires = ["setuptools>=42", "wheel"]
build-backend = "setuptools.build_meta"
EOL
    echo "pyproject.toml created."
fi

# Ensure that build and twine are installed and up to date
echo "Ensuring build and twine are installed..."
python3 -m pip install --upgrade build twine

# Extract package name from setup.py
PACKAGE_NAME=$(python3 setup.py --name)
if [ -z "$PACKAGE_NAME" ]; then
    echo "Error: Unable to determine package name from setup.py"
    deactivate
    exit 1
fi

# Get the current version on PyPI
CURRENT_VERSION=$(python3 -c "import requests; r=requests.get(f'https://pypi.org/pypi/{PACKAGE_NAME}/json'); print(r.json()['info']['version'] if r.status_code == 200 else '0.0.0')")
if [ -z "$CURRENT_VERSION" ]; then
    echo "Error: Unable to determine current version from PyPI"
    deactivate
    exit 1
fi
echo "Current version on PyPI: $CURRENT_VERSION"

# Increment the version in setup.py
NEW_VERSION=$(echo "$CURRENT_VERSION" | awk -F. '{print $1"."$2"."$3+1}')
echo "Updating setup.py with new version: $NEW_VERSION"
sed -i "s/version='$CURRENT_VERSION'/version='$NEW_VERSION'/" setup.py

# Build the package (both source and wheel)
echo "Building the package..."
python3 -m build --sdist --wheel
if [ $? -ne 0 ]; then
    echo "Error during building the package."
    deactivate
    exit 1
fi

# Upload the package to PyPI using twine
echo "Uploading the package to PyPI..."
python3 -m twine upload dist/* --skip-existing
if [ $? -ne 0 ]; then
    echo "Error during upload to PyPI."
    deactivate
    exit 1
fi

echo "Upload successful. Check PyPI for your package."

# Deactivate the virtual environment
deactivate
