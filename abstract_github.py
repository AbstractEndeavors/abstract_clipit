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
