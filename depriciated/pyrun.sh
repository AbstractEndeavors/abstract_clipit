# Run the Python script in a loop to capture and install missing modules
run_script() {
    while true; do
        # Run the Python script
        if [[ "$background_mode" == true ]]; then
            # In background mode, redirect both stdout and stderr to log file only
            python3 "$PYTHON_SCRIPT" > "$LOG_FILE" 2>&1
        else
            # In foreground mode, output to both terminal and log file using tee
            python3 "$PYTHON_SCRIPT" 2>&1 | tee "$LOG_FILE"
        fi

        # Check if the error log contains ModuleNotFoundError
        if grep -q "ModuleNotFoundError: No module named" "$LOG_FILE"; then
            # Extract the missing module name
            missing_module=$(grep "ModuleNotFoundError" "$LOG_FILE" | awk -F "'" '{print $2}')

            if [ ! -z "$missing_module" ]; then
                # Check if the module has already failed more than MAX_ATTEMPTS
                if [[ ${failed_attempts[$missing_module]} -ge $MAX_ATTEMPTS ]]; then
                    echo "Skipping $missing_module after ${failed_attempts[$missing_module]} failed attempts."
                    continue
                fi

                echo "Missing module detected: $missing_module"
                echo "Attempting to install $missing_module using pipinst..."
                echo "Running pip install in: $(which pip)"

                # Try to install the missing module using pipinst
                pipinst "$missing_module"
                
                if [ $? -eq 0 ]; then
                    echo "$missing_module successfully installed. Retrying the script..."
                    # Reset the failed attempts count if installation is successful
                    failed_attempts[$missing_module]=0
                else
                    # Increment the failure count for this module
                    failed_attempts[$missing_module]=$(( ${failed_attempts[$missing_module]} + 1 ))
                    echo "Failed to install $missing_module. Attempt ${failed_attempts[$missing_module]} of $MAX_ATTEMPTS."
                fi
            fi
        else
            # No ModuleNotFoundError, assume script ran successfully
            echo "Script ran successfully."
            break
        fi

        # Check if another error persists after trying to install the module
        if grep -q "ModuleNotFoundError: No module named" "$LOG_FILE"; then
            echo "Error persists after attempting to install the missing module."
            cat "$LOG_FILE"
        fi

        # Stop the loop if all missing modules have been handled
        if [[ ${#failed_attempts[@]} -eq 0 ]]; then
            break
        fi
    done
}