# Project context

Living working memory for this repository. Read this first on every task; update it
before finishing every task.

## What this is

`Wgt-Report-Summary` parses HTML weighting reports produced by the Unicom/IBM
Professional weighting tool and emits a compact CSV summary (one row per weighting
group/filter). Primary use: quickly see which groups failed, which rim limits need
adjusting, and which cells were "impossible" (zero -> non-zero), "extreme"
(outside the 0.32x-3.2x ratio band), or "furthest from target" (largest
percentage-point gap between the projected target percent and the achieved output
percent).

## Current layout

- `src/run_wgt_summary.py` — the single self-contained script (stdlib + `bs4`).
- `build.sh` / `build.bat` — build the release folder `dist/` (gitignored):
  copy the `.py` and every `scripts/run_*.bat`/`run_*.sh`, and rewrite each
  wrapper's `SCRIPT_PATH` so the `.py` is expected in the same folder (the
  `..\src\` / `../src/` prefix is stripped). `.bat` wrappers are normalized to
  CRLF.
- `scripts/` — three Windows `.bat` examples (paths are placeholders the user
  updates; they are not required to run as-is in the repo):
  - `run_wgt_summary_single.bat` — process one report.
  - `run_wgt_summary_multi.bat` — append several reports, listed explicitly.
  - `run_wgt_summary_scan.bat` — auto-scan `REPORT_DIR` for `Weight_*.htm`,
    with a `RECENT_HOURS` cutoff (blank = all files) to process only files
    edited within the last N hours.
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
  `.py` are expected to sit side by side, so each `.bat` declares a `SCRIPT_PATH`
  variable (renamed from `SCRIPT`) that the user updates to the real path.
- **Build step (`build.sh`/`build.bat`) (2026-11)**: produces a self-contained
  `dist/` for Windows by copying the `.py` and the `.bat` wrappers together and
  rewriting each wrapper's `SCRIPT_PATH` to `run_wgt_summary.py` (same folder).
  Wrapper config params were renamed for clarity: `OUT` -> `OUTPUT_FILENAME`,
  `SCRIPT` -> `SCRIPT_PATH`, `ONLY_RECENT` -> `RECENT_HOURS` (numeric hours;
  blank/unset = no cutoff, via `if defined`), plus a new `REPORT_DIR` first param
  that each wrapper resolves to an absolute path and echoes to the console.
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
- **Issue #1 root cause (crash)**: a weighting filter with *no* summary table
  (e.g. a failed rim with no `Input frequency` table) used to make `write_results`
  fall back to the 2-element tuple `('Exception: no table parsed', -2)`, which it
  then iterated as if it were a list of rows — so `r[1]` became the character
  `'x'` and `r[1] >= 0` raised `TypeError: '>=' not supported between instances
  of 'str' and 'int'`. Fixed on both `main` and `experimental`: leave
  `Impossible`/`Extreme` cells empty when `summary_table is None`.
- **Realistic anonymized fixture**: `tests/fixtures/dummy_weight_report.htm` is
  derived from the real report by replacing variable names and permuting every
  digit (same format/width, different values), so tests exercise the real layout
  without exposing real data.
- **"Furthest from target" column (2026-11)**: the report's second table
  `Rim weight / Output frequency / Output percent` is parsed and its third column
  (the *achieved* percent) is attached to each summary-table row as field index 7.
  Rows are ranked by `abs(achieved - projected percent)` and the top N (default 3,
  `--furthest-top`) are listed in the new CSV column. Malformed input never
  crashes: unparseable values become NaN and are skipped; a row-count or
  structure mismatch (dashed/total/target misalignment) is reported as `#N/A: ...`
  in the cell. The summary and rim-weight tables are 1:1 in order (each rim = N
  targets + a dashed row + a total row), which is the alignment this relies on.
- **"Furthest from target" vs the report's color highlight (verified 2026-11)**:
  the report itself highlights (orange `#FF8800`) the first-column *rim weight*
  when it falls outside the legend range "0.1 - 12.0". That is a *different*
  signal from this column, which ranks by the residual percentage-point gap
  `|achieved% - projected%|`. They overlap but are not identical: a cell can need
  a huge multiplier yet still converge close to its target, and a cell can
  under-converge (large % gap) while its multiplier stays inside the band. The
  %-point gap was kept by request; the distinction is documented here rather than
  conflated with the tool's highlight.

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
