#!/bin/bash

# File to store running background job PIDs
PID_FILE="/tmp/pythonRun_jobs.txt"
MAX_ATTEMPTS=2  # Maximum retries for package installations
source /home/shared/bashScripts/pip/pip_install_logger.sh
# Function to activate a Conda environment
activate_conda_env() {
    local env_name="$1"
    if [ -n "$env_name" ]; then
        echo "Activating Conda environment: $env_name"

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
        conda activate "$env_name"
    fi
}

# Function to list running background jobs
list_jobs() {
    echo "Listing running background jobs:"
    if [ ! -f "$PID_FILE" ]; then
        echo "No background jobs found."
        return
    fi

    while IFS= read -r line; do
        pid=$(echo "$line" | cut -d' ' -f1)
        script=$(echo "$line" | cut -d' ' -f2-)
        if ps -p "$pid" > /dev/null; then
            echo "PID: $pid - Script: $script"
        else
            echo "Removing finished job with PID: $pid"
            # Remove stale entries
            sed -i "/^$pid /d" "$PID_FILE"
        fi
    done < "$PID_FILE"
}

# Function to kill a background job by PID
kill_job() {
    local pid_to_kill="$1"
    if ps -p "$pid_to_kill" > /dev/null; then
        echo "Killing job with PID: $pid_to_kill"
        kill "$pid_to_kill"
        if [ $? -eq 0 ]; then
            echo "Successfully killed PID: $pid_to_kill"
            # Remove the PID from the tracking file
            sed -i "/^$pid_to_kill /d" "$PID_FILE"
        else
            echo "Failed to kill PID: $pid_to_kill"
        fi
    else
        echo "No process found with PID: $pid_to_kill"
        # Clean up stale PID entry
        sed -i "/^$pid_to_kill /d" "$PID_FILE"
    fi
}

# Function to run a Python script and handle missing modules
run_python_script() {
    local python_script="$1"
    local log_file="$2"
    local background_mode="$3"
    declare -A failed_attempts

    while true; do
        if [[ "$background_mode" == true ]]; then
            python3 "$python_script" > "$log_file" 2>&1
        else
            python3 "$python_script" 2>&1 | tee "$log_file"
        fi

        if grep -q "ModuleNotFoundError: No module named" "$log_file"; then
            missing_module=$(grep "ModuleNotFoundError" "$log_file" | awk -F "'" '{print $2}')
            if [ ! -z "$missing_module" ]; then
                if [[ ${failed_attempts[$missing_module]} -ge $MAX_ATTEMPTS ]]; then
                    echo "Skipping $missing_module after ${failed_attempts[$missing_module]} failed attempts."
                    continue
                fi

                echo "Attempting to install $missing_module using pipinst..."
                pipinst "$missing_module"

                if [ $? -eq 0 ]; then
                    echo "$missing_module successfully installed. Retrying the script..."
                    failed_attempts[$missing_module]=0
                else
                    failed_attempts[$missing_module]=$(( ${failed_attempts[$missing_module]} + 1 ))
                    echo "Failed to install $missing_module. Attempt ${failed_attempts[$missing_module]} of $MAX_ATTEMPTS."
                fi
            fi
        else
            echo "Script ran successfully."
            break
        fi

        if grep -q "ModuleNotFoundError: No module named" "$log_file"; then
            echo "Error persists after attempting to install the missing module."
            cat "$log_file"
        fi

        if [[ ${#failed_attempts[@]} -eq 0 ]]; then
            break
        fi
    done
}

# Main function to parse arguments and trigger respective tasks
pythonRun() {
    local background_mode=false
    local list_jobs_flag=false
    local kill_job_flag=false
    local conda_env=""
    local python_script=""
    local pid_to_kill=""

    while [[ "$#" -gt 0 ]]; do
        case $1 in
            -b|--background) background_mode=true ;;  # Enable background mode
            -l|--list) list_jobs_flag=true ;;  # List running background jobs
            -k|--kill) kill_job_flag=true; pid_to_kill="$2"; shift ;;  # Kill the job with specified PID
            -e|--env) conda_env="$2"; shift ;;  # Specify Conda environment
            -h|--help) 
                echo "Usage: $0 <python_script> [-b|--background] [-l|--list] [-k|--kill <PID>] [-e|--env <conda_env>]"
                exit 0
                ;;
            *) python_script="$1" ;;  # Store the Python script name
        esac
        shift
    done

    if [[ "$list_jobs_flag" == true ]]; then
        list_jobs
        exit 0
    fi

    if [[ "$kill_job_flag" == true ]]; then
        kill_job "$pid_to_kill"
        exit 0
    fi

    if [[ -n "$conda_env" ]]; then
        activate_conda_env "$conda_env"
    fi

    if [[ -z "$python_script" ]]; then
        echo "Error: No Python script specified."
        exit 1
    fi

    # Use shared directory as the default log directory
    local log_file="/home/shared/error_log.txt"

    if [[ "$background_mode" == true ]]; then
        run_python_script "$python_script" "$log_file" true &
        pid=$!
        echo "$pid $python_script" >> "$PID_FILE"
        disown
    else
        run_python_script "$python_script" "$log_file" false
    fi
}
