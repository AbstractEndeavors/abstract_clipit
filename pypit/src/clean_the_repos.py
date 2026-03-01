from .imports import *
import subprocess, sys, re, pathlib, os

MERGE_PATTERNS = ("<<<<<<<", "=======", ">>>>>>>")
_SKIP_DIRS = {".git", ".hg", ".svn", ".idea", ".vscode", "__pycache__", "dist", "build", ".venv", "venv", ".mypy_cache"}
_SKIP_SUFFIXES = {".whl", ".gz", ".zip", ".png", ".jpg", ".jpeg", ".pdf", ".so", ".pyc"}

# (optional) tell the guard to ignore git-state, or limit scan to a subtree
def ensure_clean_repo(where="(unspecified)", *, require_clean_git=False, root="."):
    offenders = {}
    for p in _iter_repo_files(root):
        if not _looks_text(p):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        # Quick skip: if file contains none of the tokens at all, move on
        if not any(tok in txt for tok in MERGE_PATTERNS):
            continue

        # Try to ignore obvious full-line conflict markers; we still want to catch real ones,
        # but avoid strings in comments for common languages.
        hits = []
        lines=[]
        for ln, line in enumerate(txt.splitlines(), 1):
            raw = line

            # crude comment stripping for common file types
            stripped = raw
            if p.suffix in {".py", ".sh"}:
                stripped = raw.split("#", 1)[0]
            elif p.suffix in {".js", ".ts", ".c", ".cpp", ".java", ".go"}:
                stripped = raw.split("//", 1)[0]
            # NOTE: We don't try to strip block comments; we want to be conservative.

            if any(tok in stripped for tok in MERGE_PATTERNS):
                # also ignore when line clearly looks like a literal string (best-effort)
                if re.search(r'["\']<<<<<<<|=======|>>>>>>>["\']', raw):
                    lines.append(line)
                    continue
                
                hits.append((ln, raw.rstrip()))
            else:
                lines.append(line)
        if hits:
            offenders[str(p)] = hits[:10]
        #write_to_file(contents = '\n'.join(lines),file_path=str(p))
    if offenders:
        lines = [f"\n🚫 Merge conflict markers detected {where}. Resolve before continuing:"]
        for path, hits in offenders.items():
            lines.append(f"  - {path}")
            for (ln, t) in hits:
                lines.append(f"      L{ln:>4}: {t}")
            if len(hits) == 10:
                lines.append("      ... (more lines truncated)")
        raise RuntimeError("\n".join(lines))

    if require_clean_git:
        checks = (
            (["git", "diff", "--quiet"], "Unstaged changes in working tree."),
            (["git", "diff", "--cached", "--quiet"], "Staged but uncommitted changes in index."),
        )
        for args, err_msg in checks:
            rc = subprocess.call(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if rc != 0:
                raise RuntimeError(err_msg)

def _looks_text(path: pathlib.Path) -> bool:
    try:
        if path.is_dir():
            return False
        if path.suffix.lower() in _SKIP_SUFFIXES:
            return False
        if path.stat().st_size > 5_000_000:
            return False
        with path.open("rb") as f:
            chunk = f.read(2048)
        return b"\x00" not in chunk
    except Exception:
        return False

def _iter_repo_files(root="."):
    root_p = pathlib.Path(root).resolve()
    for p in root_p.rglob("*"):
        # skip anything inside a skipped dir
        if any(part in _SKIP_DIRS for part in p.parts):
            continue
        yield p

