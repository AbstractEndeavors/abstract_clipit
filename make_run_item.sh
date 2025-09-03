#!/bin/bash

# Variables
DESKTOP_ENTRY_PATH="$HOME/.local/share/applications/open_with_conda.desktop"
SCRIPT_PATH="$HOME/open_with_conda.sh"

# Step 1: Create the open_with_conda.sh script
echo "Creating the Conda execution script..."
cat > "$SCRIPT_PATH" <<EOL
#!/bin/bash
# Activate the Conda environment
source ~/miniconda/bin/activate base

# Run the Python file in the activated Conda environment
python "\$1"
EOL

# Make the script executable
chmod +x "$SCRIPT_PATH"

echo "Conda execution script created at $SCRIPT_PATH"

# Step 2: Create the .desktop entry
echo "Creating the .desktop entry..."
mkdir -p "$HOME/.local/share/applications"
cat > "$DESKTOP_ENTRY_PATH" <<EOL
[Desktop Entry]
Name=Open with Conda Python
Comment=Run Python files using Conda environment
Exec=$SCRIPT_PATH %f
Icon=python
Terminal=false
Type=Application
MimeType=application/x-python-code
EOL

# Step 3: Set permissions for the .desktop file
chmod +x "$DESKTOP_ENTRY_PATH"

echo ".desktop entry created at $DESKTOP_ENTRY_PATH"

# Step 4: Add MIME type association in mimeapps.list
echo "Associating .py files with the Conda launcher..."
MIMEAPPS_PATH="$HOME/.config/mimeapps.list"

# Ensure the directory exists
mkdir -p "$(dirname "$MIMEAPPS_PATH")"

# Add the association to mimeapps.list
if grep -q "application/x-python-code" "$MIMEAPPS_PATH"; then
    # Replace the existing association
    sed -i 's|application/x-python-code=.*|application/x-python-code=open_with_conda.desktop|' "$MIMEAPPS_PATH"
else
    # Add a new association
    echo "[Default Applications]" >> "$MIMEAPPS_PATH"
    echo "application/x-python-code=open_with_conda.desktop" >> "$MIMEAPPS_PATH"
fi

echo "File association updated in $MIMEAPPS_PATH"

# Step 5: Update the desktop database
echo "Updating desktop database..."
update-desktop-database "$HOME/.local/share/applications/"

# Restart file manager (Nautilus) to apply changes
echo "Restarting file manager..."
nautilus -q

echo "Setup complete! You can now open .py files with the Conda environment."
