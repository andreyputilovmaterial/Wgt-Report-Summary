# Project context

Living working memory for this repository. Read this first on every task; update it
before finishing every task.

## What this is

`Wgt-Report-Summary` parses HTML weighting reports produced by the Unicom/IBM
Professional weighting tool and emits a compact CSV summary (one row per weighting
group/filter). Primary use: quickly see which groups failed, which rim limits need
adjusting, and which cells were "impossible" (zero -> non-zero) or "extreme"
(outside the 0.32x-3.2x ratio band).

## Current layout

- `src/run_wgt_summary.py` — the single self-contained script (stdlib + `bs4`).
- `scripts/` — three Windows `.bat` examples (paths are placeholders the user
  updates; they are not required to run as-is in the repo):
  - `run_wgt_summary_single.bat` — process one report.
  - `run_wgt_summary_multi.bat` — append several reports, listed explicitly.
  - `run_wgt_summary_scan.bat` — auto-scan `Weight_*.htm`, with an
    `ONLY_RECENT=1` toggle to process only files edited within the last 24h.
- `tests/` — pytest suite, including `fixtures/dummy_weight_report.htm` (an
  anonymized sample report).
- `tests-real-sensitive-data/` — gitignored; holds real/proprietary report inputs
  (e.g. `Weight_Report_DE.htm`) for local use.
- `docs/` — this file and `roadmap.md`.
- `docs/wgt-summary-example.png` — screenshot used in the README.

## Key decisions & reasoning

- **The tool stays a pure input -> output transform.** Given a report (or reports)
  it produces a CSV. Keep it simple and predictable: no conditional "modes" or
  orchestration logic (scanning, recency filtering, etc.) inside the Python script —
  that belongs in the wrapper `.bat`/shell scripts.
- **Script lives in `src/`** (2026-11): requested. In a release the `.bat` and
  `.py` are expected to sit side by side, so each `.bat` declares a `SCRIPT`
  variable that the user updates to the real path.
- **Append mode via `--options out_append`**: the script stays single-file per
  invocation; "many reports -> one CSV" is achieved by running it once per file
  with a shared `--out`. Multi-file scanning is an example loop in the `.bat`,
  not built into the script.
- **`--options out_reportfile_stats`** prepends `Report File` + `Last Edited`
  columns so each row is traceable to its source. It is independent of
  `out_append` (fixed a bug where it silently required `out_append`).
- **Report `.htm` files are gitignored** (`Weight_*.htm*` and the whole
  `tests-real-sensitive-data/` folder): they are inputs, not part of the repo.
  The sample `Weight_Report_DE.htm` now lives only in `tests-real-sensitive-data/`
  (gitignored) and must never be merged into `main`.
- **Empty/degenerate summary tables must not crash**: when no summary table is
  parsed, the `Impossible`/`Extreme` cells are left empty (an empty list, not a
  placeholder) instead of iterating a malformed fallback tuple.
- **Robust to degenerate/invalid input**: `clean_summary_outputs_value` returns
  NaN instead of raising on an unparseable value, and a missing `Matrix vars:`
  line no longer crashes `parse_log` (cells fall back to `???`).
- **Realistic anonymized fixture**: `tests/fixtures/dummy_weight_report.htm` is
  derived from the real report by replacing variable names and permuting every
  digit (same format/width, different values), so tests exercise the real layout
  without exposing real data.

## Gotchas

- `forfiles /D -N` selects files **older** than N days (per Microsoft docs), so it
  cannot express "edited within 24h"; the scan example uses PowerShell for that.
- The CSV header is `Weight Var` (changed from `Weight var`; cosmetic).
- `parse_log` expects summary-table rows to be tab-separated; `read_html` produces
  those tabs by joining each `<TR>` cell.

## Naming note (open)

The author is considering renaming `run_wgt_summary.py`; keep the current name for
now until a better one is chosen.

## Open questions / follow-ups

See `docs/roadmap.md`.
