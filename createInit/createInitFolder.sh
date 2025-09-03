#!/usr/bin/env bash
set -euo pipefail

### ---------------------------------------------------------------------------
### Helpers
### ---------------------------------------------------------------------------

die() { echo "Error: $*" >&2; exit 1; }

usage() {
  cat <<EOF
createinit – scaffold a TypeScript or Python module (default: ts)

USAGE:
  createinit [-k ts|py|pyutil] <module_name>

FLAGS:
  -k, --kind   Scaffold kind:
                 ts     – TypeScript module (default)
                 py     – Simple Python module
                 pyutil – Python module with utils/ and imports/ sub-packages
  -h, --help   Show this help message

EXAMPLES:
  createinit mylib                # TypeScript scaffold (default)
  createinit -k py    mylib       # Simple Python scaffold
  createinit --kind pyutil tools  # Python utils scaffold
EOF
  exit 0
}

### ---------------------------------------------------------------------------
### Clipboard helper (unchanged)
### ---------------------------------------------------------------------------

# --- replace your append_clipboard with this ---
append_clipboard() {
  local prefix="$1"
  local clip=""

  if command -v pbpaste &>/dev/null; then
    clip=$(pbpaste || true)
  elif command -v wl-paste &>/dev/null; then
    clip=$(wl-paste || true)         # Wayland
  elif command -v xclip &>/dev/null && [ -n "${DISPLAY-}" ]; then
    clip=$(xclip -selection clipboard -o || true)   # X11 only if DISPLAY set
  elif command -v xsel &>/dev/null && [ -n "${DISPLAY-}" ]; then
    clip=$(xsel --clipboard --output || true)
  fi

  if [ -z "$clip" ]; then
    # Fallback: don’t fail—emit just the prefix (or prompt)
    # read -p "Clipboard empty/unavailable. Paste now, then Enter: " -r dummy
    # clip=$(</dev/stdin)
    printf '%s\n' "$prefix"
  else
    printf '%s\n%s\n' "$prefix" "$clip"
  fi
}

# Function to get module name
get_local_name() {
  if [ -z "$1" ]; then
    echo "Error: Please provide a module name" >&2
    return 1
  fi
  echo "$1"
}


### ---------------------------------------------------------------------------
### Scaffold generators (your original bodies, trimmed for brevity)
### ---------------------------------------------------------------------------




# --- in setup_ts_module(): fix invalid import & mkdir -p everywhere ---
setup_ts_module() {
  local NAME
  NAME=$(get_local_name "$1") || return 1

  echo "Debug: Creating directories $NAME and $NAME/src"
  mkdir -p "$NAME/src"

  echo "Debug: Creating $NAME/index.ts"
  cat > "$NAME/index.ts" <<EOF
export * from './src';
EOF

  echo "Debug: Creating $NAME/imports.ts"
  cat > "$NAME/imports.ts" <<EOF
export * from './';
EOF

  echo "Debug: Creating $NAME/src/index.ts"
  cat > "$NAME/src/index.ts" <<EOF
export * from './$NAME';
EOF

  echo "Debug: Creating $NAME/src/$NAME.ts with import and clipboard content"
  # Use a valid line by default; you can switch to 'import * as Imports ...' if preferred
  append_clipboard "export * from './../imports';" > "$NAME/src/$NAME.ts"

  echo "TypeScript module '$NAME' scaffolded."
}

# --- in setup_py_module(): use -p and tolerate re-run ---
setup_py_module() {
  local NAME
  NAME=$(get_local_name "$1") || return 1

  echo "Debug: Creating directory $NAME"
  mkdir -p "$NAME"
  echo "Debug: Navigating to $NAME"
  cd "$NAME" || { echo "Error: Failed to navigate to $NAME" >&2; return 1; }

  echo "Debug: Creating __init__.py"
  printf 'from .%s import *\n' "$NAME" > __init__.py

  echo "Debug: Creating $NAME.py (clipboard if available, else empty)"
  if command -v pbpaste >/dev/null 2>&1; then
    pbpaste > "$NAME.py" || : > "$NAME.py"
  elif command -v wl-paste >/dev/null 2>&1; then
    wl-paste > "$NAME.py" || : > "$NAME.py"
  elif command -v xclip >/dev/null 2>&1 && [ -n "${DISPLAY-}" ]; then
    xclip -selection clipboard -o > "$NAME.py" || : > "$NAME.py"
  elif command -v xsel >/dev/null 2>&1 && [ -n "${DISPLAY-}" ]; then
    xsel --clipboard --output > "$NAME.py" || : > "$NAME.py"
  else
    : > "$NAME.py"
  fi

  echo "Python module '$NAME' scaffolded."
  cd - >/dev/null || true
}

# --- in setup_py_utils_module(): ensure -p; keep the rest as-is ---
setup_py_utils_module() {
  local NAME
  NAME=$(get_local_name "$1") || return 1

  echo "Debug: Creating directories $NAME, $NAME/utils, and $NAME/imports"
  mkdir -p "$NAME/utils" "$NAME/imports"

  # __init__.py for the module
  echo "Debug: Creating $NAME/__init__.py"
  cat > "$NAME/__init__.py" <<EOF
from .utils import *
EOF

  # utils/__init__.py
  echo "Debug: Creating $NAME/utils/__init__.py"
  cat > "$NAME/utils/__init__.py" <<EOF
from .utils import *
EOF

  # utils/utils.py: prefix + clipboard
  echo "Debug: Creating $NAME/utils/utils.py with import and clipboard content"
  append_clipboard "from ..imports import *" > "$NAME/utils/utils.py"

  # imports/__init__.py
  echo "Debug: Creating $NAME/imports/__init__.py"
  cat > "$NAME/imports/__init__.py" <<EOF
from .imports import *
EOF

  # imports/imports.py (empty file)
  echo "Debug: Creating $NAME/imports/imports.py"
  : > "$NAME/imports/imports.py"

  echo "Python utils module '$NAME' scaffolded."
}

### ---------------------------------------------------------------------------
### Argument parsing
### ---------------------------------------------------------------------------

KIND="ts"     # default
POSITIONALS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    -k|--kind)
      [[ $# -lt 2 ]] && die "flag '$1' expects an argument"
      KIND="$2"; shift 2
      ;;
    -h|--help) usage ;;
    -*        ) die "unknown flag '$1' (see --help)";;
    *         ) POSITIONALS+=("$1"); shift ;;
  esac
done

[[ ${#POSITIONALS[@]} -eq 1 ]] || die "missing <module_name> (see --help)"
NAME="${POSITIONALS[0]}"

case "$KIND" in
  ts     ) setup_ts_module       "$NAME" ;;
  py     ) setup_py_module       "$NAME" ;;
  pyutil ) setup_py_utils_module "$NAME" ;;
  *      ) die "invalid kind '$KIND' (use ts, py, or pyutil)" ;;
esac
