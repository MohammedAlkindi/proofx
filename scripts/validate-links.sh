#!/usr/bin/env bash
set -euo pipefail

missing=0
while IFS= read -r file; do
  while IFS= read -r ref; do
    href=$(echo "$ref" | sed -E 's/.*href="([^"]+)".*/\1/')
    case "$href" in
      http*|mailto:*|\#*|javascript:*|/http*) continue ;;
    esac
    clean=${href%%#*}
    clean=${clean%%\?*}
    path=${clean#/}
    [ -z "$path" ] && path="index.html"

    if [[ "$path" != *.* ]] && [ -e "public/$path.html" ]; then
      continue
    fi

    if [ ! -e "$path" ] && [ ! -e "public/$path" ]; then
      echo "Missing target in $file -> $href"
      missing=1
    fi
  done < <(rg -o 'href="[^"]+"' "$file")
done < <(rg --files -g '*.html' public | rg '^public/[^/]+\\.html$')

exit $missing
