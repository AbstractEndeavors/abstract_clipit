# spypit: bump -> build -> upload from current dir
spypit() {
  set -euo pipefail
  local PART="${1:-patch}"   # patch | minor | major
  local DIST_DIR="$PWD/dist"

  _die(){ printf 'Error: %s\n' "$*" >&2; return 1; }

  [[ -f pyproject.toml || -f setup.cfg || -f setup.py ]] || _die "no pyproject.toml/setup.cfg/setup.py here"

  # Ensure deps (quiet)
  python3 - <<'PY' >/dev/null 2>&1 || python3 -m pip install --user -q build twine >/dev/null 2>&1 || true
import importlib, sys
for m in ("build","twine"):
    try: importlib.import_module(m)
    except Exception: sys.exit(1)
PY

  # One Python block: detect & bump version, print export-ready lines
  local OUT
  OUT="$(
  python3 - "$PART" <<'PY'
import re, sys, configparser, tomllib
from pathlib import Path

part = sys.argv[1] if len(sys.argv)>1 else "patch"
root = Path(".").resolve()
pyproject = root / "pyproject.toml"
setup_cfg = root / "setup.cfg"
setup_py  = root / "setup.py"

def read(p): return p.read_text(encoding="utf-8")
def write(p,t): p.write_text(t, encoding="utf-8")
def semver(v):
    m = re.fullmatch(r"\s*(\d+)\.(\d+)\.(\d+)\s*", v); 
    return tuple(map(int,m.groups())) if m else None
def bump(v):
    M,m,p = semver(v) or (None,None,None)
    if M is None: raise SystemExit(f"ERR not a semver: {v}")
    if part=="major": return f"{M+1}.0.0"
    if part=="minor": return f"{M}.{m+1}.0"
    return f"{M}.{m}.{p+1}"

src = old = new = name = ""

# 1) pyproject (PEP 621)
if pyproject.exists():
    data = tomllib.loads(read(pyproject))
    proj = data.get("project", {})
    if "version" in proj and not ("dynamic" in proj and "version" in proj["dynamic"]):
        name = proj.get("name") or ""
        old  = proj["version"]; new = bump(old)
        txt = read(pyproject)
        txt = re.sub(r'(^\s*version\s*=\s*")(.*?)(")', rf'\1{new}\3', txt, flags=re.M, count=1)
        write(pyproject, txt)
        src = "pyproject"
        print(f"SRC={src}"); print(f"OLD={old}"); print(f"NEW={new}"); print(f"NAME={name}")
        sys.exit(0)

# 2) setup.cfg
if setup_cfg.exists():
    cfg = configparser.ConfigParser()
    cfg.read(setup_cfg, encoding="utf-8")
    if cfg.has_section("metadata"):
        name = cfg.get("metadata","name", fallback="")
        val  = cfg.get("metadata","version", fallback="").strip()
        m = re.match(r'attr:\s*([A-Za-z0-9_.]+)\.__version__', val)
        if not m and val:
            old = val; new = bump(old)
            cfg.set("metadata","version", new)
            with open(setup_cfg,"w",encoding="utf-8") as f: cfg.write(f)
            src = "setup.cfg"
            print(f"SRC={src}"); print(f"OLD={old}"); print(f"NEW={new}"); print(f"NAME={name}")
            sys.exit(0)
        if m:
            mod = m.group(1).replace(".","/")
            cand = (root/"src"/mod/"__init__.py")
            if not cand.exists(): cand = (root/mod/"__init__.py")
            if not cand.exists(): raise SystemExit(f"ERR cannot find {m.group(1)}.__init__.py")
            txt = read(cand)
            mo = re.search(r'^__version__\s*=\s*"([^"]+)"', txt, re.M)
            if not mo: raise SystemExit(f"ERR __version__ not found in {cand}")
            old = mo.group(1); new = bump(old)
            txt = re.sub(r'(^__version__\s*=\s*")(.*?)(")', rf'\1{new}\3', txt, flags=re.M, count=1)
            write(cand, txt)
            src = f"attr:{m.group(1)}.__version__"
            print(f"SRC={src}"); print(f"OLD={old}"); print(f"NEW={new}"); print(f"NAME={name}")
            sys.exit(0)

# 3) legacy setup.py
if setup_py.exists():
    txt = read(setup_py)
    m = re.search(r'version\s*=\s*"([^"]+)"', txt)
    if m:
        old = m.group(1); new = bump(old)
        txt = re.sub(r'(version\s*=\s*")([^"]+)(")', rf'\1{new}\3', txt, count=1)
        write(setup_py, txt)
        src = "setup.py"
        print(f"SRC={src}"); print(f"OLD={old}"); print(f"NEW={new}"); print(f"NAME=")
        sys.exit(0)

raise SystemExit("ERR version source not found")
PY
  )" || _die "version bump failed"

  # Export vars printed by Python
  eval "$OUT"

  echo "Working dir:  $PWD"
  echo "Version src:  $SRC"
  echo "Bump:         $OLD -> $NEW"
  [[ -n "${NAME:-}" ]] && echo "Package:      $NAME"

  rm -rf "$DIST_DIR"
  python3 -m build

  echo "Artifacts:"
  ls -1 "$DIST_DIR"

  # Ensure artifacts match NEW
  ls "$DIST_DIR" | grep -Eq -- "-${NEW}(\.tar\.gz|\.whl)$" \
    || _die "built artifacts do not contain version ${NEW} (your project reads version elsewhere)"

  # Upload; fail if already exists
  set +e
  UP=$(python3 -m twine upload "$DIST_DIR"/* 2>&1)
  RC=$?
  set -e
  echo "$UP"
  echo "$UP" | grep -qi "already exist" && _die "PyPI says ${NEW} already exists — bump again"
  (( RC == 0 )) || _die "twine upload failed"

  echo "✅ Uploaded ${NAME:-package} ${NEW}"
}