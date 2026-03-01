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
    # 0) SSH setup
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
        # 🔒 Guard before git commit
        ensure_clean_repo(where="runPypit/before-commit")

        commit_message = (
            f"Release {package_name}=={pypi_increment_version} @ "
            f"{check_output(['date', '-u', '+%Y-%m-%d %H:%M:%S UTC'], text=True).strip()}"
        )

        if skip_github_push:
            raise RuntimeError(
                "SKIP_GITHUB_PUSH is set — refusing to upload to PyPI "
                "because GitHub must be the source of truth."
            )

        # Commit MUST succeed
        try_commit(commit_message, git_env)

        # Push MUST succeed
        print("🚀 Pushing commit and tags to GitHub...")
        branch = current_branch(env=git_env)
        push_to_origin(branch, env=git_env)
        run_github(["git", "push", "--tags", "origin"], cwd=str(REPO_ROOT), env=git_env)
        # 🔒 Only now is PyPI allowed
        ensure_clean_repo(where="runPypit/before-upload")
        print("📤 Uploading to PyPI (twine)...")
        up_out, up_err = upload_package(package_name=package_name)
        # Final guard (you already had one here; keep it)
        ensure_clean_repo(where="runPypit/final-guard")
        print("✅ Run complete.")
        break


