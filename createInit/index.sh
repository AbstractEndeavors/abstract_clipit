#!/usr/bin/env bash
set -euo pipefail

# Function to append clipboard content with a prefix
append_clipboard() {
  local prefix="$1"
  local clip

  if command -v pbpaste >/dev/null 2>&1; then
    clip=$(pbpaste)
  elif command -v xclip >/dev/null 2>&1; then
    clip=$(xclip -selection clipboard -o)
  else
    echo "Error: no clipboard utility found (pbpaste or xclip required)" >&2
    return 1
  fi

  # Print prefix, a newline, then the clipboard contents
  printf '%s\n%s' "$prefix" "$clip"
}

# Function to set up a TypeScript module with a main file
setup_typescript_module() {
  # Check if name parameter is provided
  if [ -z "$1" ]; then
    echo "Error: Please provide a module name" >&2
    return 1
  fi

  local NAME="$1"

  # Create directories
  echo "Debug: Creating directories $NAME and $NAME/src"
  mkdir -p "$NAME/src"

  # Create index.ts for the module
  echo "Debug: Creating $NAME/index.ts"
  cat > "$NAME/index.ts" <<EOF
export * from './src';
EOF

  # Create src/index.ts
  echo "Debug: Creating $NAME/src/index.ts"
  cat > "$NAME/src/index.ts" <<EOF
export * from './$NAME';
EOF

  # Create src/$NAME.ts with import and clipboard content
  echo "Debug: Creating $NAME/src/$NAME.ts with import and clipboard content"
  append_clipboard "import * as imports from '../imports';" > "$NAME/src/$NAME.ts"

  echo "Module '$NAME' scaffolded."
}