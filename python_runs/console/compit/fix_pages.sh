#!/usr/bin/env bash
set -euo pipefail

LIST_FILE="${1:-page_list.txt}"

if [[ ! -f "$LIST_FILE" ]]; then
  echo "List file not found: $LIST_FILE"
  exit 1
fi

mapfile -t FILES <"$LIST_FILE"

for f in "${FILES[@]}"; do
  echo "Fixing $f"

  # 1a) Remove next/head import lines
  perl -0777 -i -pe 's/^\s*import\s+Head\s+from\s+["'"'"']next\/head["'"'"'];\s*\n//mg' "$f"

  # 1b) Ensure react-helmet-async import exists (insert after first import)
  perl -0777 -i -pe 'unless (/react-helmet-async/) { s/^(\s*import[^\n]*\n)/$1import { Helmet } from "react-helmet-async";\n/m }' "$f"

  # 2) Fix broken imports without quotes -> scoped aliases
  perl -0777 -i -pe 's/from\s+PageHeader\s*;/from "@PageHeader";/g; s/from\s+Body\s*;/from "@Body";/g' "$f"

  # 3) Enforce named imports for PageHeader/Body (no default)
  perl -0777 -i -pe 's/^\s*import\s+PageHeader\s+from\s+["'"'"']@PageHeader["'"'"']\s*;/import { PageHeader } from "@PageHeader";/mg; s/^\s*import\s+Body\s+from\s+["'"'"']@Body["'"'"']\s*;/import { Body } from "@Body";/mg' "$f"

  # 4) Next types -> React.FC
  perl -0777 -i -pe 's/\bNextPage\s*<\s*SourceProps\s*>\s*/React.FC<SourceProps>/g' "$f"

  # 5) Comment out getStaticProps blocks (keep original inside comment)
  perl -0777 -i -pe 's/\n\s*export\s+const\s+getStaticProps\b.*?\n}\s*;\s*/\n\/\* NEXT:getStaticProps removed for Vite\n$&\n\*\/\n/smg' "$f"

  # 6) Fix accidental duplicate <Helmet> opening tags
  perl -0777 -i -pe 's/(<Helmet>[^<]*?)<Helmet>/$1<\/Helmet>/s' "$f"

  # 7) Ensure React import is present when using React.FC
  perl -0777 -i -pe 'if (/React\.FC/ && $_ !~ /import\s+React\s+from\s+["'"'"']react["'"'"']/) { $_ = "import React from \"react\";\n" . $_ }' "$f"
done

echo "✅ Codemod complete for ${#FILES[@]} files."
