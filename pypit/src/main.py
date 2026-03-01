from .imports import *
from .pypit_utils import *
from .github_auth import *

ensure_clean_repo(where="main.py/import-guard")

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
    import time
    FATAL_PATTERNS = [
        "error: command",
        "getting requirements to build wheel: finished with status 'error'",
        "could not build wheels",
        "build backend returned an error",
        "no matching distribution found",
        "failed to build",
    ]
    new_version = new_version or get_current_version(package_name)
    max_attempts = 5
    last_output, last_stderr = "", ""
    for attempt in range(max_attempts):
        output, stderr = update_package(package_name=package_name)
        last_output, last_stderr = str(output or ""), str(stderr or "")
        combined = (last_output + last_stderr).lower()
        local_version = get_local_version(package_name)
        print(f"Local version: {local_version}, PyPI version: {new_version}")
        if local_version == new_version:
            print(f"✅ {package_name} is up-to-date with PyPI.")
            return last_output, last_stderr
        fatal = next((p for p in FATAL_PATTERNS if p in combined), None)
        if fatal:
            print(f"❌ Unrecoverable pip error ('{fatal}'). Fix the dependency then reinstall manually.")
            return last_output, last_stderr
        if attempt < max_attempts - 1:
            wait = 15 * (attempt + 1)
            print(f"Attempt {attempt + 1}/{max_attempts}: not yet synced, waiting {wait}s...")
            time.sleep(wait)
    print(f"⚠️ Could not sync to {new_version} after {max_attempts} attempts.")
    return last_output, last_stderr


def runPypit():
    # 0) gitignore + SSH setup
    ensure_gitignore()
    git_env = ensure_git_ssh()

    package_name = get_package_name()
    
    print(f"Package name: {package_name}")

    git_env = git_debug_repo_and_remote(package_name, env=git_env)

    local_version = get_local_version(package_name)
    print(f"Current local version: {local_version}")

    skip_github_push = bool(os.getenv("SKIP_GITHUB_PUSH"))
    if skip_github_push:
        raise RuntimeError(
            "SKIP_GITHUB_PUSH is set — refusing to continue. "
            "GitHub must be committed before PyPI upload."
        )

    while True:
        # 1) ensure clean
        ensure_clean_repo(where="runPypit/before-compute-version")

        # 2) compute version
        current_pypi_version = get_current_version(package_name)
        #print(f"Current version on PyPI: {current_pypi_version}")
        pypi_increment_version = get_pypi_increment_version(package_name)
        #print(f"Pypi increment version: {pypi_increment_version}")

        # 3) update setup.py
        ensure_clean_repo(where="runPypit/before-update-setup.py")
        update_setup_py_version(new_version=pypi_increment_version)

        # 4) clean old build artifacts
        directory = os.getcwd()
        src_dir = os.path.join(directory, 'src')
        remove_files = [
            os.path.join(directory, f) for f in os.listdir(directory)
            if f.endswith('.whl') or f.endswith('.tar.gz')
        ]
        remove_dirs = []
        if os.path.isdir(src_dir):
            remove_dirs += [
                os.path.join(src_dir, f) for f in os.listdir(src_dir)
                if f.endswith('.egg-info')
            ]
        remove_dirs += [os.path.join(directory, 'build'), os.path.join(directory, 'dist')]
        for d in remove_dirs:
            if os.path.isdir(d):
                shutil.rmtree(d)
        for f in remove_files:
            if os.path.exists(f):
                os.remove(f)

        # 5) build
        ensure_clean_repo(where="runPypit/before-build")
        print("🔧 Building package...")
        output, stderr = build_package()
        if output is None and stderr is None:
            raise RuntimeError("❌ Build failed — aborting before commit or PyPI upload.")
        print("✅ Build complete.")

        # 6) commit + push to github
        ensure_clean_repo(where="runPypit/before-commit")
        commit_message = (
            f"Release {package_name}=={pypi_increment_version} @ "
            f"{check_output(['date', '-u', '+%Y-%m-%d %H:%M:%S UTC'], text=True).strip()}"
        )
        try_commit(commit_message, git_env)
        print("🚀 Pushing to GitHub...")
        branch = current_branch(env=git_env)
        push_to_origin(branch, env=git_env)
        run_github(["git", "push", "--tags", "origin"], cwd=str(REPO_ROOT), env=git_env)

        # 7) upload to PyPI
        ensure_clean_repo(where="runPypit/before-upload")
        #print("📤 Uploading to PyPI (twine)...")
        try:
            up_out, up_err = upload_package(package_name=package_name)
            print("PyPI upload output:\n", up_out or "")
            if up_err:
                print("PyPI upload stderr:\n", up_err)
        except Exception as e:
            print(f"❌ PyPI upload failed: {e}")

        # 8) update local install
        try:
            print("🔁 Updating local package to match PyPI (best-effort)...")
            out, err = update_package_until_synced(package_name, pypi_increment_version)
            print("Update result:", out, err)
        except Exception as e:
            print(f"⚠️ update_package_until_synced error: {e}")

        # 9) final guard
        ensure_clean_repo(where="runPypit/final-guard")
        print("✅ Run complete.")
        break
