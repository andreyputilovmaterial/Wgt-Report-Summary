#!/usr/bin/env bash
# Build the release folder (dist/) from src/ and scripts/.
#
# Copies run_wgt_summary.py and every run_*.bat / run_*.sh wrapper into dist/,
# rewriting each wrapper's SCRIPT_PATH so the .py is expected in the same folder
# (the repo's "..\src\" / "../src/" prefix is stripped). .bat wrappers are
# normalized to CRLF so they run cleanly on Windows.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"

rm -rf dist
mkdir -p dist

cp src/run_wgt_summary.py dist/

shopt -s nullglob
for src in scripts/run_*.bat scripts/run_*.sh; do
    dest="dist/$(basename "$src")"
    "$PYTHON" - "$src" "$dest" <<'PY'
import sys

src, dst = sys.argv[1], sys.argv[2]
text = open(src, newline="").read()
text = text.replace("SCRIPT_PATH=..\\src\\", "SCRIPT_PATH=")
text = text.replace("SCRIPT_PATH=../src/", "SCRIPT_PATH=")
if dst.lower().endswith(".bat"):
    text = text.replace("\r\n", "\n").replace("\n", "\r\n")
open(dst, "w", newline="").write(text)
PY
done

echo "Built: dist/"
