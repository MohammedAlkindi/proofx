#!/usr/bin/env bash
# Validate that every internal href/src in the generated pages (src/*.html)
# resolves to a file in the deploy root, honoring Vercel cleanUrls
# (extensionless routes map to src/<path>.html).
set -euo pipefail

cd "$(dirname "$0")/.."

# Routes resolved by vercel.json rewrites rather than the filesystem.
# /auth/error -> src/auth-error.html
# /germinal   -> src/germinal.html (page lands with the ledger-viewer branch;
#                drop this entry once that merges and the file check covers it)
ALLOWLIST="/auth/error /germinal"

missing=0
checked=0

shopt -s nullglob
pages=(src/*.html)
if [ "${#pages[@]}" -eq 0 ]; then
  echo "No generated pages found under src/ — run scripts/build.sh first." >&2
  exit 1
fi

for file in "${pages[@]}"; do
  refs=$(grep -oE '(href|src)="[^"]+"' "$file" | sed -E 's/^(href|src)="([^"]+)"$/\2/' | sort -u)
  while IFS= read -r ref; do
    [ -z "$ref" ] && continue
    case "$ref" in
      http://*|https://*|//*|mailto:*|tel:*|\#*|javascript:*|data:*) continue ;;
      /_vercel/*) continue ;;
    esac

    clean=${ref%%#*}
    clean=${clean%%\?*}
    [ -z "$clean" ] && continue

    skip=0
    for allowed in $ALLOWLIST; do
      if [ "$clean" = "$allowed" ]; then
        skip=1
        break
      fi
    done
    [ "$skip" -eq 1 ] && continue

    path=${clean#/}
    [ -z "$path" ] && path="index.html"

    checked=$((checked + 1))
    base=${path##*/}
    if [ -e "src/$path" ]; then
      continue
    fi
    if [[ "$base" != *.* ]] && [ -e "src/$path.html" ]; then
      continue
    fi
    echo "Missing target in $file -> $ref"
    missing=$((missing + 1))
  done <<<"$refs"
done

if [ "$checked" -eq 0 ]; then
  echo "Validator checked zero internal references — that is itself a failure." >&2
  exit 1
fi

if [ "$missing" -gt 0 ]; then
  echo "$missing broken internal reference(s) across ${#pages[@]} pages." >&2
  exit 1
fi

echo "OK: $checked internal references across ${#pages[@]} pages all resolve."
