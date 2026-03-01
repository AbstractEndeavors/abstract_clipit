#!/bin/bash
FILE="$1"
SESSION="idle_workspace"

tmux has-session -t $SESSION 2>/dev/null || tmux new-session -d -s $SESSION

WINDOW_NAME=$(basename "$FILE")

if tmux list-windows -t $SESSION | grep -q "$WINDOW_NAME"; then
    tmux select-window -t "$SESSION:$WINDOW_NAME"
else
    tmux new-window -t $SESSION -n "$WINDOW_NAME" \
        "python -m idlelib \"$FILE\""
fi

tmux attach -t $SESSION
