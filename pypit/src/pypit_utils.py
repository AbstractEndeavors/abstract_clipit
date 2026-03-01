from .imports import *
from .clean_the_repos import *
def ensure_pyproject_toml():
    if not os.path.exists("pyproject.toml"):
        print("pyproject.toml not found. Creating pyproject.toml...")
        with open("pyproject.toml", "w") as f:
            f.write(
                "[build-system]\n"
                "requires = [\"setuptools>=42\", \"wheel\"]\n"
                "build-backend = \"setuptools.build_meta\"\n"
            )
        print("pyproject.toml created.")
GITIGNORE_ENTRIES = [
    "build/",
    "dist/",
    "logs/",
    "*.egg-info/",
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.whl",
    "*.tar.gz",
    "*.asc",
    ".env",
    ".venv/",
]

def ensure_gitignore(root="."):
    root = Path(root)
    gi = root / ".gitignore"
    
    existing = set()
    if gi.exists():
        existing = {l.strip() for l in gi.read_text().splitlines() if l.strip()}
    
    missing = [e for e in GITIGNORE_ENTRIES if e not in existing]
    if missing:
        with gi.open("a") as f:
            f.write("\n" + "\n".join(missing) + "\n")
        print(f"📝 Added {len(missing)} entries to .gitignore")

    # untrack anything that's now in .gitignore but still indexed
    result = subprocess.run(
        ["git", "ls-files", "--ignored", "--exclude-standard", "-z"],
        cwd=root, capture_output=True, text=True
    )
    tracked_noise = [f for f in result.stdout.split("\0") if f]
    if tracked_noise:
        subprocess.run(["git", "rm", "-r", "--cached", "--"] + tracked_noise, cwd=root)
        print(f"🗑️  Untracked {len(tracked_noise)} previously-committed artifact(s)")
def get_package_name(path=None):
    try:
        output, stderr = getCmdRunLocal(key="package_name", path=path)
        return output.strip()
    except subprocess.CalledProcessError:
        print("Error: Unable to determine package name from setup.py")

def get_current_version(package_name):
    try:
        response = requests.get(f"https://pypi.org/pypi/{package_name}/json")
        if response.status_code == 200:
            return response.json()["info"]["version"]
        else:
            print(f"Package {package_name} not found on PyPI. Using version 0.0.0.")
            return "0.0.0"
    except requests.RequestException as e:
        print(f"Error fetching current version from PyPI: {e}")
    return None

def get_local_version(package_name, path=None):
    try:
        output, stderr = getCmdRunLocal(key="local_version", package_name=package_name, path=path)
        for line in output.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
        print(f"Package {package_name} is not installed locally. {output}")
        return output
    except Exception as e:
        print(f"Error checking local version for {package_name}: {e}")

def get_increment_version(version):
    parts = version.split(".")
    if not all(part.isdigit() for part in parts):
        print(f"Invalid version format: {version}")
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)

def get_local_increment_version(package_name):
    version = get_local_version(package_name)
    return get_increment_version(version)

def get_pypi_increment_version(package_name):
    version = get_current_version(package_name)
    return get_increment_version(version)

def update_version_in_setup(current_version, new_version):
    with open("setup.py", "r") as f:
        setup_content = f.read()
    updated_content = re.sub(
        f"version=['\"]{current_version}['\"]",
        f"version='{new_version}'",
        setup_content,
    )
    with open("setup.py", "w") as f:
        f.write(updated_content)
    print(f"Updated setup.py with new version: {new_version}")

# pypit_utils.py — build_package: make signing optional, don't abort on missing key
def build_package(package_name=None, path=None):
    try:
        output, stderr = getCmdRunLocal(key="build_package", package_name=package_name, path=path)
        print(f"Package built successfully: {output}")
        for file in os.listdir("dist"):
            if file.endswith(('.whl', '.tar.gz')):
                result = subprocess.run(
                    ["gpg", "--detach-sign", "--armor", f"dist/{file}"],
                    capture_output=True, text=True
                )
                if result.returncode != 0:
                    print(f"⚠️ GPG signing skipped for {file}: {result.stderr.strip()}")
        return output, stderr
    except Exception as e:
        print(f"Error during building the package: {e}")
    return None, None

def upload_package(package_name=None, path=None):
    """Upload the package to PyPI (non-interactive)."""
    try:
        subprocess.run(
            [
                "python3", "-m", "twine", "upload",
                "--repository", "pypi",
                "--non-interactive",
                "dist/*",
            ],
            check=True,
        )
        print("✅ Package uploaded to PyPI.")
    except subprocess.CalledProcessError:
        print("❌ PyPI upload failed.")
        exit(1)

def update_setup_py_version(setup_path="setup.py", new_version="0.0.10"):
    p = Path(setup_path)
    txt = p.read_text(encoding="utf-8")
    for line in txt.split('\n'):
        cleanline = line.replace(' ', '')
        if 'version=' in cleanline:
            txt = txt.replace(f"version{line.split('version')[1].split(',')[0]},", f"version='{new_version}',")
            p.write_text(txt, encoding="utf-8")
            return
def update_package_until_synced(package_name, new_version=None):
    new_version = new_version or get_current_version(package_name)
    max_attempts = 5
    for attempt in range(max_attempts):
        output, stderr = update_package(package_name=package_name)
        local_version = get_local_version(package_name)
        print(f"Local version: {local_version}, PyPI version: {new_version}")
        if local_version == new_version:
            print(f"{package_name} is up-to-date with PyPI.")
            return output, stderr
        print(f"Attempt {attempt+1}/{max_attempts}: version not yet synced, waiting...")
        import time; time.sleep(10)
    print(f"⚠️ Could not sync to {new_version} after {max_attempts} attempts.")
    return output, stderr
def update_package(package_name=None, path=None):
    try:
        output, stderr = getCmdRunLocal(key="update_package", package_name=package_name, path=path)
        print(f"Package updated successfully: {output}")
        return str(output), str(stderr)
    except Exception as e:
        print(f"Error during update: {e}")
    return None, None

def update_to_specific(package_name, new_version, path=None):
    cmd = ["python3", "-m", "pip", "install", "--no-cache-dir", f"{package_name}=={new_version}"]
    proc = subprocess.run(cmd, cwd=path or os.getcwd(), capture_output=True, text=True)
    print(proc.stdout); print(proc.stderr)
    return proc.stdout, proc.stderr
