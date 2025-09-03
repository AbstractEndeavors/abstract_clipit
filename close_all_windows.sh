#!/bin/bash

# Function to close specific editor windows by keyword
close_python_windows() {
    # Use a keyword that is unique to your editor (update as needed)
    windows=$(wmctrl -l | grep -E "YourEditorKeyword|Python" | awk '{print $1}')

    # Loop through each window found
    for win in $windows; do
        # Bring the window to the foreground
        wmctrl -i -a "$win"

        # Send the keyboard shortcut to close the window (e.g., Ctrl+W or Alt+F4)
        xdotool windowactivate "$win"
        xdotool key --window "$win" ctrl+w  # Adjust this based on the actual shortcut used by the editor

        # Short delay to avoid command overlap
        sleep 0.5
    done
}

# Execute the function
close_python_windows
