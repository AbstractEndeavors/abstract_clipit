#!/usr/bin/env bash
set -e

echo "=== Setting up VS Code F5 → IDLE (conda) ==="

### Paths
USER_HOME="$HOME"
VSCODE_USER_DIR="$USER_HOME/.config/Code/User"
KEYBINDINGS="$VSCODE_USER_DIR/keybindings.json"
SETTINGS="$VSCODE_USER_DIR/settings.json"

PROJECT_DIR="$(pwd)"
VSCODE_PROJECT_DIR="$PROJECT_DIR/.vscode"
TASKS_FILE="$VSCODE_PROJECT_DIR/tasks.json"

IDLE_CONDA="/usr/local/bin/idle-conda"

### 1. Ensure idle-conda exists
if ! command -v idle-conda >/dev/null 2>&1; then
  echo "Installing idle-conda..."

  sudo tee "$IDLE_CONDA" >/dev/null <<'EOF'
#!/bin/bash
set -e

export PATH="$HOME/miniconda/bin:$PATH"
source "$HOME/miniconda/etc/profile.d/conda.sh"
conda activate base

PYTHON="$(which python)"

if [ $# -gt 0 ]; then
  exec "$PYTHON" -m idlelib "$1" &
else
  exec "$PYTHON" -m idlelib &
fi
EOF

  sudo chmod 755 "$IDLE_CONDA"
else
  echo "idle-conda already installed"
fi

### 2. Create .vscode/tasks.json
echo "Writing .vscode/tasks.json..."
mkdir -p "$VSCODE_PROJECT_DIR"

cat > "$TASKS_FILE" <<'EOF'
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run Python in IDLE (conda)",
      "type": "shell",
      "command": "idle-conda",
      "args": ["${file}"],
      "group": {
        "kind": "build",
        "isDefault": true
      },
      "presentation": {
        "reveal": "never"
      },
      "problemMatcher": []
    }
  ]
}
EOF

### 3. Ensure keybindings.json exists
mkdir -p "$VSCODE_USER_DIR"
[ -f "$KEYBINDINGS" ] || echo "[]" > "$KEYBINDINGS"

### 4. Add F5 keybinding (idempotent)
echo "Configuring F5 keybinding..."

python3 - <<EOF
import json, pathlib

kb = pathlib.Path("$KEYBINDINGS")
data = json.loads(kb.read_text())

entry = {
  "key": "f5",
  "command": "workbench.action.tasks.runTask",
  "args": "Run Python in IDLE (conda)",
  "when": "editorTextFocus && editorLangId == 'python'"
}

if entry not in data:
    data.append(entry)

kb.write_text(json.dumps(data, indent=2))
EOF

### 5. Fix settings.json (remove invalid command/args if present)
echo "Fixing settings.json..."

python3 - <<EOF
import json, pathlib

p = pathlib.Path("$SETTINGS")
if not p.exists():
    p.write_text("{}")

data = json.loads(p.read_text())

# Remove invalid keys if user added them
data.pop("command", None)
data.pop("args", None)

data["python.debuggerEnabled"] = False

p.write_text(json.dumps(data, indent=2))
EOF

echo
echo "=== DONE ==="
echo
echo "Next steps:"
echo "1. Restart VS Code COMPLETELY"
echo "2. Open a .py file inside: $PROJECT_DIR"
echo "3. Press F5"
echo
echo "Expected: IDLE opens immediately with the file loaded."
