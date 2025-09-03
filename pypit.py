import os
import subprocess
import requests
import re
import shutil
from pathlib import Path
from subprocess import check_output
import os, subprocess

def _run(cmd, cwd=None, check=True):
    """Run a list command, return (stdout, stderr)."""
    p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if check and p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, cmd, p.stdout, p.stderr)
    return (p.stdout or "").strip(), (p.stderr or "").strip()

def _current_branch():
    # Best effort; default to main if detached/new
    out, _ = _run(["git", "symbolic-ref", "--short", "HEAD"], check=False)
    return out.strip() or "main"

def ensure_git_repo_and_remote(package_name: str):
    """Init repo if needed; ensure 'origin' exists and is SSH."""
    if not os.path.exists(".git"):
        _run(["git", "init"])
        # Default branch to main (modern GitHub default)
        _run(["git", "checkout", "-B", "main"])
    # Does origin exist?
    remotes_out, _ = _run(["git", "remote", "-v"], check=False)
    has_origin = any(line.startswith("origin\t") for line in remotes_out.splitlines())
    ssh_url = f"git@github.com:AbstractEndeavors/{package_name}.git"
    if not has_origin:
        _run(["git", "remote", "add", "origin", ssh_url], check=True)
    else:
        # Normalize to SSH if it isn't already
        if "github.com/AbstractEndeavors/" in remotes_out and "git@github.com:" not in remotes_out:
            _run(["git", "remote", "set-url", "origin", ssh_url], check=True)

def stage_and_commit_if_changes(message: str):
    _run(["git", "add", "-A"])
    # Only commit if there are changes staged
    status_out, _ = _run(["git", "status", "--porcelain"], check=False)
    if status_out.strip():
        _run(["git", "commit", "-m", message])
        return True
    return False

def push_to_origin(branch: str):
    # First push might need -u; detect if upstream is set
    rev_parse_out, _ = _run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], check=False)
    if rev_parse_out.strip() == "":
        _run(["git", "push", "-u", "origin", branch])
    else:
        _run(["git", "push", "origin", branch])
def getcmd(key, package_name=None, new_version=None):
    CMD_PRELOADS = {
        "upload": ["python3", "-m", "twine", "upload", "--sign", "dist/*", "--skip-existing"],
        "package_name": ["python3", "setup.py", "--name"],
        "local_version": ["pip", "show", f"{package_name}"],
        "build_package": ["python3", "-m", "build", "--sdist", "--wheel"],
        "update_specific": ["bash", "-i", "-c", f"pipit {package_name}=={new_version}"],
        "update_package": ["pip", "install", f"{package_name}", "--upgrade"],
    }
    return CMD_PRELOADS.get(key)

def run_local_cmd(cmd, path=None):
    if path:
        path = os.path.abspath(path)
        if not os.path.isdir(path):
            raise ValueError(f"Specified path does not exist or is not a directory: {path}")
    else:
        path = os.getcwd()
    
    try:
        result = subprocess.run(
            ' '.join(cmd),
            shell=True,
            capture_output=True,
            text=True,
            cwd=path,
            check=True
        )
        return result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.stdout, e.stderr
    except Exception as e:
        raise RuntimeError(f"Failed to execute command: {e}")

def run_local_command(cmd: str, path: str=None) -> str:
    path = path or os.getcwd()
    try:
        proc = subprocess.run(cmd, cwd=path, capture_output=True, text=True)
        return (proc.stdout or ""), (proc.stderr or "")
    except Exception as e:
        return f"❌ run_local_cmd error: {e}\n", ""

def getCmdRunLocal(key, package_name=None, new_version=None, path=None):
    cmd = getcmd(key=key, package_name=package_name, new_version=new_version)
    stdout, stderr = run_local_cmd(cmd=cmd, path=path)
    return stdout, stderr

def getCommandRunLocal(key, package_name=None, new_version=None, path=None):
    cmd = getcmd(key=key, package_name=package_name, new_version=new_version)
    stdout, stderr = run_local_command(cmd=cmd, path=path)
    return stdout, stderr

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

def build_package(package_name=None, path=None):
    try:
        output, stderr = getCmdRunLocal(key="build_package", package_name=package_name, path=path)
        print(f"Package built successfully: {output}")
        # Sign the built distributions
        for file in os.listdir("dist"):
            if file.endswith(('.whl', '.tar.gz')):
                subprocess.run(["gpg", "--detach-sign", "--armor", f"dist/{file}"], check=True)
        return output, stderr
    except Exception as e:
        print(f"Error during building the package: {e}")
    return None, None

def upload_package(package_name=None, path=None):
    try:
        output, stderr = getCommandRunLocal(key="upload", package_name=package_name, path=path)
        print(f"Package uploaded successfully: {output}")
        return output, stderr
    except Exception as e:
        print(f"Error during upload to PyPI: {e}")
    return None, None

def update_setup_py_version(setup_path="setup.py", new_version="0.0.10"):
    p = Path(setup_path)
    txt = p.read_text(encoding="utf-8")
    for line in txt.split('\n'):
        cleanline = line.replace(' ', '')
        if 'version=' in cleanline:
            txt = txt.replace(f"version{line.split('version')[1].split(',')[0]},", f"version='{new_version}',")
            p.write_text(txt, encoding="utf-8")
            return

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

def update_to_specific_via_alias(package_name, new_version, path=None):
    sh = f"source ~/.bashrc; pipit {package_name}=={new_version}"
    proc = subprocess.run(
        ["bash", "-lc", sh],
        cwd=path or os.getcwd(),
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
    )
    print(proc.stdout); print(proc.stderr)
    return proc.stdout, proc.stderr

def update_package_until_synced(package_name, new_version=None):
    new_version = new_version or get_current_version(package_name)
    while True:
        output, stderr = update_package(package_name=package_name)
        local_version = get_local_version(package_name)
        print(f"Local version: {local_version}, PyPI version: {new_version}")
        if local_version == new_version:
            print(f"{package_name} is up-to-date with PyPI.")
            return output, stderr
        print(f"Updating {package_name} to match PyPI version...")
        return output, stderr

def runPypit():

    # Retrieve package name
    package_name = get_package_name()
    print(f"Package name: {package_name}")

    # Ensure Git is initialized and SSH remote is set
    ensure_git_repo_and_remote(package_name)

    local_version = get_local_version(package_name)
    print(f"Current local version: {local_version}")
    print(f"Current local version: {local_version}")
    
    while True:
        # Get current version from PyPI
        current_pypi_version = get_current_version(package_name)
        print(f"Current version on PyPI: {current_pypi_version}")
        
        # Increment version
        pypi_increment_version = get_pypi_increment_version(package_name)
        print(f"Pypi Increment version: {pypi_increment_version}")
        
        # Update setup.py with new version
        update_setup_py_version(new_version=pypi_increment_version)
        
        # Clean previous builds
        directory = os.getcwd()
        dirlist = os.listdir(directory)
        src_dir = os.path.join(directory, 'src')
        srclist = os.listdir(src_dir)
        
        remove_files = [os.path.join(directory, file) for file in dirlist if file.endswith('.whl')]
        remove_dirs = [os.path.join(src_dir, file) for file in srclist if file.endswith('.egg-info')]
        remove_dirs.append(os.path.join(directory, 'build'))
        remove_dirs.append(os.path.join(directory, 'dist'))
        
        for remove_dir in remove_dirs:
            if os.path.isdir(remove_dir):
                shutil.rmtree(remove_dir)
        for remove_file in remove_files:
            if os.path.exists(remove_file):
                os.remove(remove_file)
        
        
        # Build the package
        output, stderr = build_package()

        # Commit and push to GitHub (only if changed)
        commit_message = (
            f"Deploy version {pypi_increment_version} at "
            f"{check_output(['date', '-u', '+%Y-%m-%d %H:%M:%S UTC'], text=True).strip()}"
        )
        did_commit = stage_and_commit_if_changes(commit_message)
        branch = _current_branch()
        if did_commit:
            push_to_origin(branch)
        else:
            print("No changes to commit; skipping push.")

        # Upload the package to PyPI
        output, stderr = upload_package()

        if 'because it appears to already exist' in str(output) or 'Requirement already satisfied' in str(stderr):
            version = output.split('(')[-1].split(')')[0]
            print(f"bad version == {version}")
        else:
            output, stderr = update_package_until_synced(package_name, pypi_increment_version)
            print(f"package updated: \noutput = {output}\n{stderr}")
            break

if __name__ == "__main__":
    runPypit()
