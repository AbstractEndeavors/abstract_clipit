# Default to foreground execution
background_mode=false
list_jobs=false
kill_job=false
pid_to_kill=""
conda_env=""

# File to store running background job PIDs
PID_FILE="/tmp/pythonRun_jobs.txt"

# Parse optional arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -b|--background) background_mode=true ;;  # Enable background mode
        -l|--list) list_jobs=true ;;  # List running background jobs
        -k|--kill) kill_job=true; pid_to_kill="$2"; shift ;;  # Kill the job with specified PID
        -e|--env) conda_env="$2"; shift ;;  # Specify Conda environment
        -h|--help) 
            echo "Usage: $0 <python_script> [-b|--background] [-l|--list] [-k|--kill <PID>] [-e|--env <conda_env>]"
            echo "Options:"
            echo "  -b, --background    Run the script in background, logging output to a file"
            echo "  -l, --list          List all running background jobs"
            echo "  -k, --kill <PID>    Kill the background job with the specified PID"
            echo "  -e, --env <conda_env> Specify the Conda environment to activate"
            exit 0
            ;;
        *) PYTHON_SCRIPT="$1" ;;  # Store the Python script name
    esac
    shift
done

# List running background jobs
if [[ "$list_jobs" == true ]]; then
    # [Code for listing jobs remains the same]
    # ...
    exit 0
fi

# Kill a background job by PID
if [[ "$kill_job" == true ]]; then
    # [Code for killing jobs remains the same]
    # ...
    exit 0
fi

# Check if the Python script is provided as an argument
if [ -z "$PYTHON_SCRIPT" ]; then
    echo "Error: No Python script specified."
    echo "Usage: $0 <python_script> [-b|--background] [-l|--list] [-k|--kill <PID>] [-e|--env <conda_env>]"
    exit 1
fi

# Activate the Conda environment if specified
if [ -n "$conda_env" ]; then
    echo "Activating Conda environment: $conda_env"

    # Initialize Conda
    __conda_setup="$('/opt/conda/bin/conda' 'shell.bash' 'hook' 2> /dev/null)"
    if [ $? -eq 0 ]; then
        eval "$__conda_setup"
    else
        if [ -f "/opt/conda/etc/profile.d/conda.sh" ]; then
            . "/opt/conda/etc/profile.d/conda.sh"
        else
            export PATH="/opt/conda/bin:$PATH"
        fi
    fi
    unset __conda_setup

    # Activate the specified environment
    conda activate "$conda_env"
fi

# Check if a Conda environment is active
if [[ -z "$CONDA_DEFAULT_ENV" ]]; then
    echo "No conda environment is active. Please activate an environment first."
    exit 1
else
    echo "Active Conda environment: $CONDA_DEFAULT_ENV"
    echo "Python executable: $(which python3)"
    echo "Pip executable: $(which pip)"
fi

# Explicitly activate the Conda environment (optional but helps ensure consistency)
source activate "$CONDA_DEFAULT_ENV"

# Source the pipinst function from pip_install_logger.sh
source '/home/shared/bashScripts/pip/pip_install_logger.sh'

# Get the current working directory and log file
WORKING_DIR=$(pwd)
LOG_FILE="$WORKING_DIR/error_log.txt"

# Check if the specified Python script exists in the current directory
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: Python script '$PYTHON_SCRIPT' not found in the current directory ($WORKING_DIR)."
    exit 1
fi

# Declare an associative array to track failed installation attempts
declare -A failed_attempts

# Maximum number of retries for failed installations
MAX_ATTEMPTS=2

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

# Run the script either in the background or foreground
if [[ "$background_mode" == true ]]; then
    echo "Running the script in the background. Logs will be written to $LOG_FILE"
    run_script &
    pid=$!
    # Store the PID and the script in the PID_FILE
    echo "$pid $PYTHON_SCRIPT" >> "$PID_FILE"
    disown  # Ensure the background process continues running after the script exits
else
    echo "Running the script in the foreground."
    run_script
fi