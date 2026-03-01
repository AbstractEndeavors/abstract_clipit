from .imports import *

# ------------------------------------------------------------------------------
# Resolve repository root (directory containing .git)
# ------------------------------------------------------------------------------



# ------------------------------------------------------------------------------
# Subprocess helpers — env threads through everything
# ------------------------------------------------------------------------------

def _run(cmd, cwd=None, check=True, env=None):
    """Run a list command, return (stdout, stderr)."""
    p = subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)
    if check and p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, cmd, p.stdout, p.stderr)
    return (p.stdout or "").strip(), (p.stderr or "").strip()

def _git(cmd, check=True, env=None):
    """Run a git command from repo root with optional env."""
    return _run(["git", *cmd], cwd=str(REPO_ROOT), check=check, env=env)

# ------------------------------------------------------------------------------
# SSH helpers
# ------------------------------------------------------------------------------

def ensure_ssh_key(key_path=None):
    key_path = os.path.expanduser(key_path or get_git_key_path())
    subprocess.run(["ssh-agent", "-s"], check=False, stdout=subprocess.PIPE, text=True)
    p = subprocess.run(["ssh-add", key_path], text=True, capture_output=True)
    if p.returncode != 0 and "already" not in (p.stderr or ""):
        print(f"⚠️ ssh-add failed: {p.stderr.strip()}")
    else:
        print(f"✅ SSH key {key_path} loaded into agent")

def ensure_ssh_config_for_github(key_path=None):
    key_path = os.path.expanduser(key_path or get_git_key_path())
    cfg_path = os.path.expanduser(get_ssh_config_path())
    os.makedirs(os.path.dirname(cfg_path), exist_ok=True)
    block = (
        "Host github.com\n"
        "  User git\n"
        f"  IdentityFile {key_path}\n"
        "  IdentitiesOnly yes\n"
    )
    try:
        txt = ""
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
                txt = f.read()
        if "Host github.com" not in txt:
            with open(cfg_path, "a", encoding="utf-8") as f:
                f.write("\n" + block)
            print("🛠️ wrote github.com SSH stanza to ~/.ssh/config")
    except Exception as e:
        print(f"⚠️ couldn't edit ~/.ssh/config: {e}")

def git_env_with_key(key_path=None):
    key_path = os.path.expanduser(key_path or get_git_key_path())
    env = os.environ.copy()
    env["GIT_SSH_COMMAND"] = f"ssh -i {key_path} -o IdentitiesOnly=yes"
    return env

def ensure_git_ssh():
    ensure_ssh_config_for_github(get_git_key_path())
    ensure_ssh_key(get_git_key_path())
    return git_env_with_key(get_git_key_path())

# ------------------------------------------------------------------------------
# GitHub API helpers
# ------------------------------------------------------------------------------

def github_api_headers(i):
    tok = get_owner_tok(i)
    if not tok:
        raise RuntimeError("GITHUB_TOKEN not set; cannot create GitHub repo automatically.")
    return {
        "Authorization": f"Bearer {tok}",
        "Accept": "application/vnd.github+json",
    }

def get_github_login(i):
    r = requests.get("https://api.github.com/user", headers=github_api_headers(i), timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"Could not determine GitHub user: {r.status_code} {r.text}")
    return r.json()["login"]

def repo_exists(i, name: str) -> bool:
    owner = get_owner_name(i)
    url = f"https://api.github.com/repos/{owner}/{name}"
    r = requests.get(url, headers=github_api_headers(i), timeout=20)
    return r.status_code == 200

def create_repo(i, name: str, *, private=False, is_org=True):
    if is_org:
        owner = get_owner_name(i)
        url = f"https://api.github.com/orgs/{owner}/repos"
        body = {"name": name, "private": private, "auto_init": False, "has_issues": True, "has_projects": False, "has_wiki": False}
    else:
        url = "https://api.github.com/user/repos"
        body = {"name": name, "private": private, "auto_init": False}
    r = requests.post(url, headers=github_api_headers(i), data=json.dumps(body), timeout=20)
    if r.status_code not in (201, 202):
        raise RuntimeError(f"GitHub repo create failed ({r.status_code}): {r.text}")

def ensure_remote_repo(package_name: str, prefer_org_owner: int = 2, private=False, env=None) -> str:
    owner = get_owner_name(prefer_org_owner)
    try:
        if not repo_exists(prefer_org_owner, package_name):
            create_repo(prefer_org_owner, package_name, private=private, is_org=True)
        return f"git@github.com:{owner}/{package_name}.git"
    except Exception:
        i = prefer_org_owner - 1
        user = get_github_login(i)
        if not repo_exists(i, package_name):
            create_repo(i, package_name, private=private, is_org=False)
        return f"git@github.com:{user}/{package_name}.git"

# ------------------------------------------------------------------------------
# Git repo setup
# ------------------------------------------------------------------------------

def current_branch(env=None):
    out, _ = _git(["symbolic-ref", "--short", "HEAD"], check=False, env=env)
    return out.strip() or "main"

def ensure_git_repo_and_remote(package_name: str, env=None):
    if not (REPO_ROOT / ".git").exists():
        _git(["init"], env=env)

    branch_out, _ = _git(["symbolic-ref", "--short", "HEAD"], check=False, env=env)
    if not branch_out.strip():
        print("⚠️ Detached HEAD — attempting checkout of branch 'main'")
        out, err = _git(["checkout", "-B", "main"], check=False, env=env)
        # Verify it worked
        branch_out, _ = _git(["symbolic-ref", "--short", "HEAD"], check=False, env=env)
        if not branch_out.strip():
            raise RuntimeError(
                f"Still in detached HEAD after checkout attempt. "
                f"Run `git checkout -B main` manually in {REPO_ROOT}. "
                f"checkout stderr: {err}"
            )
        print(f"✅ Now on branch: {branch_out.strip()}")

    remotes_out, _ = _git(["remote", "-v"], check=False, env=env)
    has_origin = any(line.startswith("origin\t") for line in remotes_out.splitlines())
    ssh_url = f"git@github.com:AbstractEndeavors/{package_name}.git"

    if not has_origin:
        _git(["remote", "add", "origin", ssh_url], env=env)
    elif "github.com/AbstractEndeavors/" in remotes_out and "git@github.com:" not in remotes_out:
        _git(["remote", "set-url", "origin", ssh_url], env=env)

def git_debug_dump(env=None):
    out = subprocess.run(["git", "remote", "-v"], text=True, capture_output=True, env=env)
    print("== git remote -v ==\n" + (out.stdout or out.stderr))
    b = subprocess.run(["git", "symbolic-ref", "--short", "HEAD"], text=True, capture_output=True, env=env)
    print("== branch ==\n" + (b.stdout or b.stderr))
    s = subprocess.run(["git", "status", "--porcelain"], text=True, capture_output=True, env=env)
    print("== status ==\n" + (s.stdout or s.stderr))
    t = subprocess.run(["ssh", "-T", "git@github.com"], text=True, capture_output=True, env=env)
    print("== ssh -T git@github.com ==\n" + (t.stdout or "") + (t.stderr or ""))

def git_debug_repo_and_remote(package_name, env=None):
    git_env = env or ensure_git_ssh()
    ensure_git_repo_and_remote(package_name, env=git_env)
    git_debug_dump(env=git_env)
    return git_env

def set_repo_ssh_key_for_this_repo(key_path=None, env=None):
    key_path = os.path.expanduser(key_path or get_git_key_path())
    subprocess.run(
        ["git", "config", "core.sshCommand", f"ssh -i {key_path} -o IdentitiesOnly=yes"],
        check=False, env=env
    )

# ------------------------------------------------------------------------------
# Commit / push
# ------------------------------------------------------------------------------

def stage_and_commit_if_changes(message: str, env=None):
    _git(["add", "-A"], env=env)
    status_out, _ = _git(["status", "--porcelain"], check=False, env=env)
    if status_out.strip():
        _git(["commit", "-m", message], env=env)
        return True
    return False

# github_auth.py — push_to_origin: distinguish "nothing to push" from "push succeeded"
def push_to_origin(branch: str, env=None):
    _run(["git", "fetch", "origin"], cwd=str(REPO_ROOT), check=False, env=env)
    _run(["git", "pull", "--rebase", "origin", branch], cwd=str(REPO_ROOT), check=False, env=env)

    up_ok = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"],
        cwd=str(REPO_ROOT), capture_output=True, text=True, env=env
    ).returncode == 0

    cmd = ["git", "push"] + (["-u"] if not up_ok else []) + ["origin", branch]
    out, err = _run(cmd, cwd=str(REPO_ROOT), check=False, env=env)
    combined = (out or "") + "\n" + (err or "")

    if "Permission denied (publickey)" in combined:
        raise RuntimeError("SSH key not accepted.")
    if "fatal:" in combined.lower() or "error:" in combined.lower():
        raise RuntimeError(f"git push failed:\n{combined}")
    
    # "Everything up-to-date" means no commit was pushed — surface this clearly
    if "up-to-date" in combined or "up to date" in combined:
        print("ℹ️ git push: remote already up-to-date (no new commits pushed)")
        return False  # caller can distinguish
    return True

def _try_stage_commit_push(commit_message: str, git_env: dict):
    did_commit = False
    push_ok = False
    push_err = None

    try:
        did_commit = stage_and_commit_if_changes(commit_message, env=git_env)
    except Exception as e:
        print(f"⚠️ stage_and_commit_if_changes failed: {e}")

    try:
        branch = current_branch(env=git_env)
        push_to_origin(branch, env=git_env)
        push_ok = True
    except Exception as e:
        push_err = str(e)
        print(f"⚠️ git push failed: {push_err}")

    return did_commit, push_ok, push_err

def try_commit(commit_message, git_env):
    try:
        did_commit, pushed, push_err = _try_stage_commit_push(commit_message, git_env)
        print(f"Did commit locally: {did_commit}, Push succeeded: {pushed}")
        if push_err:
            print(f"Push error (non-fatal): {push_err}")
    except Exception as e:
        print(f"⚠️ Unexpected error during commit/push: {e}")
