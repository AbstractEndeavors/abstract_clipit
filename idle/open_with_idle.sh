#!/usr/bin/env bash
set -e

FILE="$(realpath "$1")"
SESSION="idle_workspace"

if ! command -v tmux >/dev/null 2>&1; then
    echo "❌ tmux is not installed"
    exit 1
fi

PYTHON_BIN="$(which python)"
WINDOW_NAME="$(basename "$FILE")"

tmux has-session -t "$SESSION" 2>/dev/null || \
    tmux new-session -d -s "$SESSION"

if tmux list-windows -t "$SESSION" -F "#{window_name}" | grep -Fxq "$WINDOW_NAME"; then
    tmux select-window -t "$SESSION:$WINDOW_NAME"
else
    tmux new-window -t "$SESSION" -n "$WINDOW_NAME" \
        "$PYTHON_BIN -m idlelib \"$FILE\""
fi

tmux attach -t "$SESSION"
