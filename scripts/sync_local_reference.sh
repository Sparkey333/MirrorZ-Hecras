#!/usr/bin/env bash
# Sync local HEC-RAS / Breaking-the-Code materials into docs/reference/
# (gitignored). Safe to re-run. Skips common installer binaries by default.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${ROOT}/docs/reference"
SRC_DEFAULT="/Users/ansom/Downloads/HECRAS-Breaking Hecras Code"
SRC="${1:-$SRC_DEFAULT}"
INCLUDE_INSTALLERS="${INCLUDE_INSTALLERS:-0}"

mkdir -p \
  "${DEST}/breaking-hecras-code" \
  "${DEST}/hec-ras-install" \
  "${DEST}/hec-ras-examples" \
  "${DEST}/other"

if [[ ! -d "${SRC}" ]]; then
  cat <<EOF
Source not found: ${SRC}

This script is meant to run on the Mac (or any host) that has your Downloads
folder. Cloud agents cannot see /Users/ansom/...

Usage:
  ./scripts/sync_local_reference.sh
  ./scripts/sync_local_reference.sh "/path/to/HECRAS-Breaking Hecras Code"
  INCLUDE_INSTALLERS=1 ./scripts/sync_local_reference.sh
EOF
  exit 1
fi

echo "Source: ${SRC}"
echo "Dest:   ${DEST}"
echo

# Heuristic sort: PDFs/Excel → book; Example Data trees → examples;
# installers → install (optional); everything else → other.
shopt -s nullglob
for path in "${SRC}"/* "${SRC}"/.*; do
  base="$(basename "${path}")"
  [[ "${base}" == "." || "${base}" == ".." ]] && continue

  lower="$(printf '%s' "${base}" | tr '[:upper:]' '[:lower:]')"

  if [[ -f "${path}" && "${lower}" =~ \.(exe|msi|dmg|pkg|iso)$ ]]; then
    if [[ "${INCLUDE_INSTALLERS}" == "1" ]]; then
      echo "installer → hec-ras-install/: ${base}"
      cp -R "${path}" "${DEST}/hec-ras-install/"
    else
      echo "skip installer (set INCLUDE_INSTALLERS=1 to copy): ${base}"
    fi
    continue
  fi

  if [[ "${lower}" =~ breaking|goodell|hecras.?code|\.pdf$|\.xlsm?$|\.xls$ ]]; then
    echo "book/notes → breaking-hecras-code/: ${base}"
    cp -R "${path}" "${DEST}/breaking-hecras-code/"
    continue
  fi

  if [[ "${lower}" =~ example|steady|application|beavcrek|critcrek|hec.?data ]]; then
    echo "examples → hec-ras-examples/: ${base}"
    cp -R "${path}" "${DEST}/hec-ras-examples/"
    continue
  fi

  if [[ "${lower}" =~ install|setup|hec-?ras ]]; then
    if [[ "${INCLUDE_INSTALLERS}" == "1" ]]; then
      echo "install bundle → hec-ras-install/: ${base}"
      cp -R "${path}" "${DEST}/hec-ras-install/"
    else
      echo "skip likely install bundle: ${base}"
    fi
    continue
  fi

  echo "other → other/: ${base}"
  cp -R "${path}" "${DEST}/other/"
done

cat <<EOF

Done. Review docs/reference/ and move mis-sorted items if needed.
Remember: docs/reference/** is gitignored (except README.md).
Next: open docs/FORWARD_PLAN.md and map book recipes / example projects
into MirrorZ JSON under examples/.
EOF
