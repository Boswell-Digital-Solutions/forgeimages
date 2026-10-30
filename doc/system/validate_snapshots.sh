#!/usr/bin/env bash
set -euo pipefail

PARTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$PARTS_DIR/../.." && pwd)"
ASSEMBLED_OUTPUT="${1:-$ROOT_DIR/doc/imgSYSTEM.md}"
MANIFEST="$PARTS_DIR/system_manifest.json"

require_contains() {
  local file="$1"
  local needle="$2"
  local label="$3"
  if ! grep -Fq -- "$needle" "$file"; then
    echo "snapshot validation failed: $label missing in $file" >&2
    echo "expected: $needle" >&2
    exit 1
  fi
}

require_absent() {
  local file="$1"
  local needle="$2"
  local label="$3"
  if grep -Fq -- "$needle" "$file"; then
    echo "snapshot validation failed: $label still present in $file" >&2
    echo "unexpected: $needle" >&2
    exit 1
  fi
}

require_same_set() {
  local label="$1"
  local left="$2"
  local right="$3"
  if [ "$left" != "$right" ]; then
    echo "snapshot validation failed: $label" >&2
    diff <(printf '%s\n' "$left") <(printf '%s\n' "$right") >&2 || true
    exit 1
  fi
}

# Canonical identity: index, build script and manifest declare one designation.
require_contains "$PARTS_DIR/_index.md" "**Designation:** img" "index designation"
require_contains "$PARTS_DIR/_index.md" "BDS Documentation Protocol v2.0" "index protocol"
require_contains "$PARTS_DIR/_index.md" 'Primary output: `doc/imgSYSTEM.md`' "index primary output"
require_contains "$PARTS_DIR/BUILD.sh" 'DESIGNATION="img"' "build designation"
require_contains "$MANIFEST" '"schema": "bds.repo_doc_system_manifest.v1"' "manifest schema"
require_contains "$MANIFEST" '"designation": "img"' "manifest designation"
require_contains "$MANIFEST" '"compiled_artifact": "doc/imgSYSTEM.md"' "manifest compiled artifact"
require_absent  "$PARTS_DIR/_index.md" 'Primary output: `doc/SYSTEM.md`' "index legacy primary output"
require_absent  "$PARTS_DIR/_index.md" 'Primary output: `doc/IMGSYSTEM.md`' "index uppercase primary output"
require_absent  "$PARTS_DIR/_index.md" 'Command: `bash doc/SYSTEM.md`' "index legacy doc/SYSTEM.md command"

# Stale compiled outputs must not reappear beside the canonical one.
for stale in "$ROOT_DIR/SYSTEM.md" "$ROOT_DIR/doc/SYSTEM.md" "$ROOT_DIR/doc/fiSYSTEM.md"; do
  if [ -e "$stale" ]; then
    echo "snapshot validation failed: stale compiled output present: ${stale#"$ROOT_DIR"/}" >&2
    exit 1
  fi
done

# Chapter sets: files on disk, the _index.md table, and the manifest must agree.
DISK_CHAPTERS="$(find "$PARTS_DIR" -mindepth 1 -maxdepth 1 -type f -name '[0-9][0-9]-*.md' | sed 's#.*/##' | LC_ALL=C sort)"
INDEX_CHAPTERS="$(grep -oE '^\| §[0-9]+ \| `[0-9][0-9]-[a-z0-9-]+\.md`' "$PARTS_DIR/_index.md" | grep -oE '[0-9][0-9]-[a-z0-9-]+\.md' | LC_ALL=C sort)"
MANIFEST_CHAPTERS="$(grep -oE '"source_file": "[0-9][0-9]-[a-z0-9-]+\.md"' "$MANIFEST" | grep -oE '[0-9][0-9]-[a-z0-9-]+\.md' | LC_ALL=C sort)"
require_same_set "_index.md table does not match chapter files" "$DISK_CHAPTERS" "$INDEX_CHAPTERS"
require_same_set "system_manifest.json does not match chapter files" "$DISK_CHAPTERS" "$MANIFEST_CHAPTERS"
[ -z "$(printf '%s\n' "$DISK_CHAPTERS" | cut -c1-2 | uniq -d)" ] || {
  echo "snapshot validation failed: duplicate chapter number" >&2
  exit 1
}

# Each chapter's heading carries the section number its filename and index row give it.
while IFS= read -r chapter; do
  number=$((10#${chapter:0:2}))
  require_contains "$PARTS_DIR/_index.md" "| §${number} | \`${chapter}\`" "index row for ${chapter}"
  if ! head -n 1 "$PARTS_DIR/$chapter" | grep -Eq "^# §${number} — "; then
    echo "snapshot validation failed: ${chapter} heading is not '# §${number} — ...'" >&2
    exit 1
  fi
done <<< "$DISK_CHAPTERS"

# Assembled artifact must carry doctrine and not still declare legacy output.
test -f "$ASSEMBLED_OUTPUT"
require_contains "$ASSEMBLED_OUTPUT" "Document version" "assembled document version header"
require_contains "$ASSEMBLED_OUTPUT" "**Designation:** img" "assembled designation"
require_contains "$ASSEMBLED_OUTPUT" 'Primary output: `doc/imgSYSTEM.md`' "assembled primary output"
require_contains "$ASSEMBLED_OUTPUT" "BDS Documentation Protocol v2.0" "assembled protocol"
require_contains "$ASSEMBLED_OUTPUT" "truth classes" "assembled truth classes"
require_absent  "$ASSEMBLED_OUTPUT" 'Primary output: `doc/SYSTEM.md`' "assembled legacy primary output"
require_absent  "$ASSEMBLED_OUTPUT" 'Root `SYSTEM.md` is the primary assembled reference.' "assembled legacy primary reference"
require_absent  "$ASSEMBLED_OUTPUT" "registry-generated bootstrap scaffold" "assembled bootstrap placeholder"

echo "snapshot validation passed: $ASSEMBLED_OUTPUT"
