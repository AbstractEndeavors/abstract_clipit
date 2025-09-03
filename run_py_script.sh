#!/usr/bin/expect

set timeout -1

# Manually read the .env file
set env_file [open "/home/gamook/.env" r]
while {[gets $env_file line] >= 0} {
    if {[regexp {^\s*SUDO_PASS\s*=\s*(.+)\s*$} $line match password]} {
        set SUDO_PASS $password
    }
}
close $env_file

# Check if a script path was provided
if { $argc != 1 } {
    puts "Usage: $argv0 /path/to/python_script.py"
    exit 1
}

set script_path [lindex $argv 0]

spawn sudo -S python3 $script_path
expect "password for *:"
send "$SUDO_PASS\r"
interact
