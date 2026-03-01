#!/usr/bin/env bash
set -euo pipefail

# ---- config (edit if paths differ) ------------------------------------------
USER_HOME="${HOME}"

# Local build target(s)
LOCAL_MAIN="/home/computron/Documents/pythonTools/modules/src/modules/abstract_ide/run_ide_local.py"
LOCAL_FALLBACK="/home/computron/bashScripts/python/python_runs/ide/run/local/start.py"

# PyPI target(s)
PIP_START="/home/computron/bashScripts/python/python_runs/ide/run/pypi/start.py"   # calls startIdeConsole()
PIP_RUN="/home/computron/bashScripts/python/python_runs/ide/run/pypi/run.py"       # optional wrapper

# Where to put the single entrypoint wrapper
BIN_DIR="${USER_HOME}/bin"
WRAPPER="${BIN_DIR}/abstract-ide"

# .desktop output
APPS_DIR="${USER_HOME}/.local/share/applications"
DESKTOP_LOCAL="${APPS_DIR}/abstract-ide-local.desktop"
DESKTOP_PYPI="${APPS_DIR}/abstract-ide-pypi.desktop"

# Optional: fixed conda env name; leave empty to use current shell env
CONDA_ENV_NAME=""

# ---- helper: choose python ---------------------------------------------------
pick_python() {
  # prefer active conda env if available
  if command -v conda >/dev/null 2>&1; then
    if [[ -n "${CONDA_ENV_NAME}" ]]; then
      # shellcheck disable=SC1091
      source "$(conda info --base)/etc/profile.d/conda.sh"
      conda activate "${CONDA_ENV_NAME}"
    fi
  fi

  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
  elif command -v python >/dev/null 2>&1; then
    echo "python"
  else
    echo "ERROR: no python found on PATH" >&2
    return 1
  fi
}

# ---- ensure dirs -------------------------------------------------------------
mkdir -p "${BIN_DIR}" "${APPS_DIR}"

# ---- chmod files you already have -------------------------------------------
chmod +x \
  "/home/computron/bashScripts/python/python_runs/ide/run/pypi/start.py" \
  "/home/computron/bashScripts/python/python_runs/ide/run/pypi/run.py" \
  "/home/computron/bashScripts/python/python_runs/ide/run/pypi/launch.sh" \
  "/home/computron/bashScripts/python/python_runs/ide/run/local/start.py" \
  "/home/computron/bashScripts/python/python_runs/ide/run/local/run.py" \
  "/home/computron/bashScripts/python/python_runs/ide/run/local/launch.sh" \
  || true

# ---- write the single entrypoint wrapper ------------------------------------
cat > "${WRAPPER}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-}"
shift || true

PY_LOCAL_MAIN="/home/computron/Documents/pythonTools/modules/src/modules/abstract_ide/run_ide_local.py"
PY_LOCAL_FB="/home/computron/bashScripts/python/python_runs/ide/run/local/start.py"
PY_PIP_START="/home/computron/bashScripts/python/python_runs/ide/run/pypi/start.py"
PY_PIP_RUN="/home/computron/bashScripts/python/python_runs/ide/run/pypi/run.py"

pick_python() {
  if command -v conda >/dev/null 2>&1; then
    if [[ -n "${CONDA_ENV_NAME:-}" ]]; then
      # shellcheck disable=SC1091
      source "$(conda info --base)/etc/profile.d/conda.sh"
      conda activate "${CONDA_ENV_NAME}"
    fi
  fi
  if command -v python3 >/dev/null 2>&1; then echo python3; elif command -v python >/dev/null 2>&1; then echo python; else echo ""; fi
}

PY=$(pick_python)
[[ -z "${PY}" ]] && { echo "no python found"; exit 1; }

case "${MODE}" in
  local)
    if [[ -f "${PY_LOCAL_MAIN}" ]]; then
      exec "${PY}" "${PY_LOCAL_MAIN}" "$@"
    elif [[ -f "${PY_LOCAL_FB}" ]]; then
      exec "${PY}" "${PY_LOCAL_FB}" "$@"
    else
      echo "Local entry not found." >&2; exit 2
    fi
    ;;
  pypi)
    # Prefer your conda-aware runner if present; else call start.py directly
    if [[ -f "${PY_PIP_RUN}" ]]; then
      exec "${PY}" "${PY_PIP_RUN}" "$@"
    elif [[ -f "${PY_PIP_START}" ]]; then
      exec "${PY}" "${PY_PIP_START}" "$@"
    else
      echo "PyPI entry not found." >&2; exit 2
    fi
    ;;
  *)
    echo "Usage: abstract-ide {local|pypi} [args...]"
    exit 64
    ;;
esac
EOF

chmod +x "${WRAPPER}"

# ---- create .desktop launchers ----------------------------------------------
cat > "${DESKTOP_LOCAL}" <<EOF
[Desktop Entry]
Type=Application
Name=Abstract IDE (Local)
Comment=Run local Abstract IDE build
Exec=${WRAPPER} local
Terminal=true
Categories=Development;Utility;
Icon=utilities-terminal
EOF

cat > "${DESKTOP_PYPI}" <<EOF
[Desktop Entry]
Type=Application
Name=Abstract IDE (PyPI)
Comment=Run Abstract IDE from PyPI launcher
Exec=${WRAPPER} pypi
Terminal=true
Categories=Development;Utility;
Icon=utilities-terminal
EOF

chmod 644 "${DESKTOP_LOCAL}" "${DESKTOP_PYPI}"

# ---- finish -----------------------------------------------------------------
echo "✅ Installed:"
echo "  • ${WRAPPER}"
echo "  • ${DESKTOP_LOCAL}"
echo "  • ${DESKTOP_PYPI}"
echo
echo "Run:"
echo "  abstract-ide local    # local tree"
echo "  abstract-ide pypi     # pypi path"
echo
echo "If you need a specific conda env, edit CONDA_ENV_NAME in this script."
