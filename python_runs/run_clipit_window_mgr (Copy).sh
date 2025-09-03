#!/usr/bin/env bash
# ----------------------------------------------------------
# run_clipit_gui.sh
#
#   Usage examples
#   --------------
#   ./run_clipit_gui.sh                 # same as “both”
#   ./run_clipit_gui.sh gui             # GUI only
#   ./run_clipit_gui.sh clipit          # clipboard watcher only
#   ./run_clipit_gui.sh both            # run both
#   ./run_clipit_gui.sh --detach gui    # run GUI, detached from terminal
#   ./run_clipit_gui.sh -d              # run both, detached
#
#   Flags
#   -----
#   -d | --detach   Launch in the background (no terminal attachment)
#   -h | --help     Show this help
# ----------------------------------------------------------

set -euo pipefail

##########  FUNCTIONS  ##########
usage() {
  cat <<EOF
Usage: $0 [clipit|gui|both] [-d|--detach]

  clipit   Run abstract_clipit.run_clipit() only
  gui      Run abstract_gui.start_window_info_gui() only
  both     Run both (default) – clipit in background, GUI in foreground
  -d, --detach
           Detach from the current terminal and keep running
EOF
  exit 1
}

run_clipit() {
  python - <<'PY'
from abstract_clipit import run_clipit
run_clipit()
PY
}

run_gui() {
  python - <<'PY'
from abstract_gui import start_window_info_gui
start_window_info_gui()
PY
}

##########  ARG PARSING  ##########
mode="both"
detach=false

for arg in "$@"; do
  case "$arg" in
    clipit|gui|both) mode="$arg" ;;
    -d|--detach)     detach=true ;;
    -h|--help)       usage ;;
    *) echo "Unknown option: $arg"; usage ;;
  esac
done

##########  SELF-DETACH  ##########
if $detach; then
  log="${HOME}/run_clipit_gui.log"
  # Re-exec in a brand-new session, silence stdin, capture stdout/stderr
  setsid "$0" "$mode" >"$log" 2>&1 < /dev/null &
  echo "Launched '$mode' in background. Logging to $log"
  exit 0
fi

##########  MAIN LAUNCHER  ##########
case "$mode" in
  clipit)
    run_clipit
    ;;

  gui)
    run_gui
    ;;

  both)
    # --- Start clipboard watcher in background ---
    run_clipit &
    CLIP_PID=$!

    # --- Ensure it stops when GUI ends or on Ctrl-C ---
    cleanup() {
      if kill -0 "$CLIP_PID" 2>/dev/null; then
        kill "$CLIP_PID"
        wait "$CLIP_PID" 2>/dev/null || true
      fi
    }
    trap cleanup EXIT INT TERM

    # --- Launch GUI (blocks) ---
    run_gui
    ;;
esac
