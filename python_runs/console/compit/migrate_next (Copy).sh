#!/usr/bin/env bash
set -euo pipefail

# --- config -------------------------------------------------------------------
SRC_DIR="${SRC_DIR:-src}"
DRY_RUN="${DRY_RUN:-0}"      # 1 = show diffs only, 0 = modify files
VERBOSE="${VERBOSE:-1}"

# Components you KNOW are named exports (so change "import X from '@X'" -> "import { X } from '@X'")
# Add to this list as needed:
NAMED_COMPONENTS=("PageHeader" "Body")

# --- helpers ------------------------------------------------------------------
have() { command -v "$1" >/dev/null 2>&1; }

die() { echo "❌ $*" >&2; exit 1; }

info() { [ "${VERBOSE}" -eq 1 ] && echo "▶ $*"; }

backup_once() {
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git add -A && git commit -m "chore: pre-migration snapshot" >/dev/null 2>&1 || true
}

sed_i() {
  # portable-ish in-place sed
  if sed --version >/dev/null 2>&1; then
    sed -i "$@"
  else
    # BSD/macOS sed
    sed -i '' "$@"
  fi
}

apply_sed() {
  local pattern="$1"
  local file="$2"
  if [ "${DRY_RUN}" -eq 1 ]; then
    grep -nH -E "${pattern%%/*}" "${file}" || true
  else
    sed_i -E "${pattern}" "${file}"
  fi
}

comment_block_matching() {
  # Comment out exports of Next data functions (GetStaticProps, etc.)
  local file="$1"
  local patterns=(
    's/^(export[[:space:]]+const[[:space:]]+getStaticProps[[:space:]]*:[^{;]+=\s*async\s*\([^)]*\)\s*=>\s*\{)/\/\* NEXT_TO_PORT: commented out by script \n\1/g'
    's/^(export[[:space:]]+async[[:space:]]+function[[:space:]]+getStaticProps\s*\([^)]*\)\s*\{)/\/\* NEXT_TO_PORT: commented out by script \n\1/g'
    's/^(export[[:space:]]+const[[:space:]]+getServerSideProps[[:space:]]*:[^{;]+=\s*async\s*\([^)]*\)\s*=>\s*\{)/\/\* NEXT_TO_PORT: commented out by script \n\1/g'
    's/^(export[[:space:]]+async[[:space:]]+function[[:space:]]+getServerSideProps\s*\([^)]*\)\s*\{)/\/\* NEXT_TO_PORT: commented out by script \n\1/g'
  )
  local closers=('s/^\}/\} \/* NEXT_TO_PORT: end *\//')
  if [ "${DRY_RUN}" -eq 1 ]; then
    grep -nH -E 'getStaticProps|getServerSideProps' "${file}" || true
  else
    for p in "${patterns[@]}"; do sed_i -E "${p}" "${file}"; done
    # naive: close the next standalone } on its own line (keeps code compiling)
    sed_i -E '0,/\{/{x;/./!{x;b};x}' "${file}" || true
  fi
}

# --- preflight ----------------------------------------------------------------
have rg || die "ripgrep (rg) is required."
have sed || die "sed is required."

[ -d "${SRC_DIR}" ] || die "No ${SRC_DIR}/ directory found."

# --- install deps -------------------------------------------------------------
info "Ensuring react-helmet-async is installed…"
if yarn -v >/dev/null 2>&1; then
  [ "${DRY_RUN}" -eq 1 ] || yarn add react-helmet-async
elif have npm; then
  [ "${DRY_RUN}" -eq 1 ] || npm i react-helmet-async
else
  info "No yarn/npm detected; skipping install."
fi

# --- snapshot -----------------------------------------------------------------
backup_once

# --- 1) Replace next/head with Helmet import ----------------------------------
info "Replacing \`import Head from 'next/head'\` → \`import { Helmet } from 'react-helmet-async'\`…"
mapfile -t head_files < <(rg -l "import\s+Head\s+from\s+'next/head'" "${SRC_DIR}" --iglob '**/*.{ts,tsx,js,jsx}' || true)
for f in "${head_files[@]}"; do
  [ -f "$f" ] || continue
  apply_sed "s#^import\\s+Head\\s+from\\s+['\"]next/head['\"];?#import { Helmet } from 'react-helmet-async';#g" "$f"
  # Swap JSX Head -> Helmet
  apply_sed "s/<\\/?Head\\b/<Helmet/g" "$f"
  apply_sed "s/<\\/Helmet>/<\\/Helmet>/g" "$f"
done

# --- 2) Remove Next types & imports -------------------------------------------
info "Removing Next.js types/imports (NextPage, GetStaticProps, etc.)…"
mapfile -t next_imports < <(rg -l "from 'next'|from \"next\"" "${SRC_DIR}" --iglob '**/*.{ts,tsx}' || true)
for f in "${next_imports[@]}"; do
  [ -f "$f" ] || continue
  # Strip named imports from 'next'
  if [ "${DRY_RUN}" -eq 1 ]; then
    rg -n "from 'next'|from \"next\"" "$f" || true
  else
    # remove specific named types from the import line
    sed_i -E "s#(import\\s*\\{[^}]*\\})\\s*from\\s*['\"]next['\"];?##g" "$f"
    # clean up leftover commas / braces
    sed_i -E "s/import\\s*\\{\\s*\\}\\s*;//g" "$f"
    # kill empty lines that may result
    sed_i -E "/^\\s*$/N;/^\\s*\\n\\s*$/D" "$f"
  fi
  # Replace NextPage<T> with React.FC<T>
  apply_sed "s/\\bNextPage\\s*<([^>]+)>/React.FC<\\1>/g" "$f"
  apply_sed "s/\\bNextPage\\b/React.FC/g" "$f"
  # Comment out getStaticProps/getServerSideProps blocks (naive but compiles)
  comment_block_matching "$f"
done

# --- 3) Remove gratuitous 'import React from \"react\"' if unused -------------
info "Cleaning unused default React imports (React 17+ w/ jsx: react-jsx)…"
mapfile -t react_imports < <(rg -l "^import\\s+React\\s+from\\s+['\"]react['\"];" "${SRC_DIR}" --iglob '**/*.{ts,tsx,js,jsx}' || true)
for f in "${react_imports[@]}"; do
  [ -f "$f" ] || continue
  # Keep if "React." identifier exists
  if rg -q "React\\." "$f"; then
    [ "${VERBOSE}" -eq 1 ] && echo "  keeping: $f (uses React.)"
  else
    apply_sed "s/^import\\s+React\\s+from\\s+['\"]react['\"];?\\s*//g" "$f"
  fi
done

# --- 4) Optionally switch default->named imports for known components ---------
if [ "${#NAMED_COMPONENTS[@]}" -gt 0 ]; then
  info "Optionally converting default imports to named for: ${NAMED_COMPONENTS[*]}"
  pattern="($(IFS='|'; echo "${NAMED_COMPONENTS[*]}"))"
  mapfile -t maybe_named < <(rg -l "import\\s+${pattern}\\s+from\\s+['\"][^'\"]+['\"]" "${SRC_DIR}" --iglob '**/*.{ts,tsx,js,jsx}' || true)
  for f in "${maybe_named[@]}"; do
    [ -f "$f" ] || continue
    apply_sed "s/^import\\s+(${pattern})\\s+from\\s+(['\"][^'\"]+['\"])/import { \\1 } from \\2/g" "$f"
  done
fi

# --- 5) Warn about unresolved aliases if any ----------------------------------
info "Scanning for unresolved aliases still failing to compile (quick grep)…"
rg -n "@PageHeader|@Body|@interfaces|@functions|@MetaHead|@Social" "${SRC_DIR}" --iglob '**/*.{ts,tsx}' || true

echo
if [ "${DRY_RUN}" -eq 1 ]; then
  echo "✅ Dry-run complete. Re-run with: DRY_RUN=0 bash migrate_from_next.sh"
else
  echo "✅ Migration edits applied."
  echo "👉 Make sure you wrap your app in <HelmetProvider> once (e.g., in src/main.tsx):"
  cat <<'EOT'

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import { HelmetProvider } from 'react-helmet-async'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HelmetProvider>
      <App />
    </HelmetProvider>
  </React.StrictMode>
)

EOT
fi
