from .imports import *
from .pypit_utils import *
from .github_auth import *
abs_path = os.path.abspath(__name__)
ensure_clean_repo(where=f"{abs_path}/import-guard")
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

    # Errors that mean "retry won't help, stop now"
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

        # Detect unrecoverable pip failure — retrying is pointless
        fatal = next((p for p in FATAL_PATTERNS if p in combined), None)
        if fatal:
            print(f"❌ Unrecoverable pip error detected ('{fatal}'). Aborting sync loop.")
            print(f"   Likely cause: a dependency of {package_name} failed to build.")
            print(f"   Fix the dependency issue, then reinstall manually.")
            return last_output, last_stderr

        # Version not yet available on PyPI CDN — wait and retry
        if attempt < max_attempts - 1:
            wait = 15 * (attempt + 1)  # back off: 15s, 30s, 45s...
            print(f"Attempt {attempt + 1}/{max_attempts}: not yet synced, waiting {wait}s...")
            time.sleep(wait)

    print(f"⚠️ Could not sync to {new_version} after {max_attempts} attempts (CDN lag likely).")
    return last_output, last_stderr


def runPypit():
    # 0) SSH setup
    ensure_gitignore()
    git_env = ensure_git_ssh()

    package_name = get_package_name()
    enforce_psycopg3_dependency()
    print(f"Package name: {package_name}")

    git_env = git_debug_repo_and_remote(package_name, env=git_env)

    local_version = get_local_version(package_name)
    print(f"Current local version: {local_version}")

    skip_github_push = bool(os.getenv("SKIP_GITHUB_PUSH"))

    while True:
        # 🔒 ensure clean before any version/builder mutations
        ensure_clean_repo(where="runPypit/before-compute-version")

        current_pypi_version = get_current_version(package_name)
        print(f"Current version on PyPI: {current_pypi_version}")

        pypi_increment_version = get_pypi_increment_version(package_name)
        print(f"Pypi increment version: {pypi_increment_version}")

        # 🔒 ensure still clean before rewriting files
        ensure_clean_repo(where="runPypit/before-update-setup.py")
        update_setup_py_version(new_version=pypi_increment_version)

        # Clean previous builds (your existing code)
        
        directory = os.getcwd()
        src_dir = os.path.join(directory, 'src')
        # remove old artifacts
        remove_files = [os.path.join(directory, file) for file in os.listdir(directory) if file.endswith('.whl') or file.endswith('.tar.gz')]
        remove_dirs = []
        if os.path.isdir(src_dir):
            remove_dirs += [os.path.join(src_dir, file) for file in os.listdir(src_dir) if file.endswith('.egg-info')]
        remove_dirs += [os.path.join(directory, 'build'), os.path.join(directory, 'dist')]

        for remove_dir in remove_dirs:
            if os.path.isdir(remove_dir):
                shutil.rmtree(remove_dir)
        for remove_file in remove_files:
            if os.path.exists(remove_file):
                os.remove(remove_file)

        # 🔒 guard again before build
        ensure_clean_repo(where="runPypit/before-build")
        print("🔧 Building package...")
        output, stderr = build_package()
        if output is None and stderr is None:
            print("⚠️ Build may have failed. Check build output or logs.")
        else:
            print("✅ Build complete.")

        # Upload to PyPI FIRST — so uploads don't depend on git push success
        # 🔒 guard before upload
        ensure_clean_repo(where="runPypit/before-upload")
        print("📤 Uploading to PyPI (twine)...")
        try:
            up_out, up_err = upload_package(package_name=package_name)
            print("PyPI upload output:\n", up_out or "")
            if up_err:
                print("PyPI upload stderr:\n", up_err)
        except Exception as e:
            print(f"❌ Upload to PyPI raised an exception: {e}")
            # we continue: maybe build succeeded but upload failed transiently

        # After upload attempt, update local install (optionally) and then try to push to github,
        # but do not let push failures block completion.
        # After upload...
        commit_message = (
            f"Deploy version {pypi_increment_version} at "
            f"{check_output(['date', '-u', '+%Y-%m-%d %H:%M:%S UTC'], text=True).strip()}"
        )

        if skip_github_push:
            print("ℹ️ SKIP_GITHUB_PUSH is set — skipping git commit/push steps.")
            # If you still want to commit locally even when skipping push, you can uncomment:
            try:
                stage_and_commit_if_changes(commit_message, env=git_env)
            except Exception as e:
                print(f"⚠️ committing locally failed: {e}")
        else:
            # 🔒 guard before any git staging/commit/push
            ensure_clean_repo(where="runPypit/before-commit-push")
            try_commit(commit_message, git_env)

        # Optionally: attempt to update installed package until local matches requested (non-blocking)
        try:
            print("🔁 Updating local package to match PyPI (best-effort)...")
            out, err = update_package_until_synced(package_name, pypi_increment_version)
            print("Update result:", out, err)
        except Exception as e:
            print(f"⚠️ update_package_until_synced error: {e}")
        # Final guard (you already had one here; keep it)
        ensure_clean_repo(where="runPypit/final-guard")
        print("✅ Run complete.")
        break


