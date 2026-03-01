mkdir -p ~/.local/bin
cat > ~/.local/bin/abstract-ide-launch.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

# --- config ---
MINICONDA="/home/computron/miniconda"
ENV_NAME="base"     # <-- change to your env name
SCRIPT="/home/computron/bashScripts/python/python_runs/ide/run_abstract_ide.py"
WORKDIR="$(dirname "$SCRIPT")"
LOG_DIR="$HOME/.cache/abstract-ide"
mkdir -p "$LOG_DIR"

# --- conda init + env ---
# Use profile.d so it works outside login shells (desktop launchers)
/usr/bin/env bash -lc "source \"$MINICONDA/etc/profile.d/conda.sh\" \
  && conda activate \"$ENV_NAME\" \
  && cd \"$WORKDIR\" \
  && nohup python3 \"$SCRIPT\" >\"$LOG_DIR/app.out\" 2>\"$LOG_DIR/app.err\" & disown"

exit 0
EOF
chmod +x ~/.local/bin/abstract-ide-launch.sh