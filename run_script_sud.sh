#!/usr/bin/expect

set timeout -1
set env_path '/home/gamook/.env'

# Check if a script path was provided
if { $argc != 1 } {
    puts "Usage: $argv0 /path/to/python_script.py"
    exit 1
}

set script_path [lindex $argv 0]

spawn sudo -S python3 $script_path
expect "password for *:"
send "$env(SUDO_PASS)\r"
interact

