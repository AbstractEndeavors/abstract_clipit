git_doctor_push() {
  set -e
  echo "== remote -v"; git remote -v || true
  echo "== branch"; git symbolic-ref --short HEAD || true
  echo "== status --porcelain"; git status --porcelain || true
  echo "== whoami"; git config user.name; git config user.email || true
  echo "== test SSH"; ssh -T git@github.com || true

  # ensure repo initialized and remote in SSH form
  if [ ! -d .git ]; then git init; fi
  if ! git remote | grep -q '^origin$'; then
    pkg="$(python3 setup.py --name 2>/dev/null || echo abstract_clipit)"
    git remote add origin "git@github.com:AbstractEndeavors/${pkg}.git"
  fi

  # ensure at least one commit
  if [ -z "$(git rev-parse --verify HEAD 2>/dev/null)" ]; then
    git add -A
    git commit -m "chore: initial commit"
  fi

  # choose branch
  b="$(git symbolic-ref --short HEAD 2>/dev/null || echo main)"
  # set upstream on first push
  if ! git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
    git push -u origin "$b"
  else
    git pull --rebase origin "$b" || true
    git push origin "$b"
  fi
}
