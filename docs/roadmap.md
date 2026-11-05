# Roadmap / TODO

Living TODO list. Add ideas freely; triage at the end of each task.

## Ideas / follow-ups

- Decide a better name for `run_wgt_summary.py` (author is not satisfied with it).
- Consider packaging (`pyproject.toml`) if the script grows into multiple modules.
- [x] Enhance parsing and capture the worst rims — implemented as the
  "Furthest from target" column (parses the `Rim weight / Output frequency /
  Output percent` table; see `docs/project-context.md`).
- [x] Address https://github.com/andreyputilovmaterial/Wgt-Report-Summary/issues/1
  (crash on reports with a no-summary-table filter) — fixed on both `main` and
  `experimental`; see `docs/project-context.md`.
- [x] Add `build.sh` / `build.bat` to assemble `dist/` (copy `.py` + wrappers,
  rewrite `SCRIPT_PATH` to same-folder, CRLF-normalize `.bat`).
- [x] Rework wrapper config params (`REPORT_DIR` first, `OUTPUT_FILENAME`,
  `SCRIPT_PATH`, `RECENT_HOURS`), print the scan folder to the console, and add a
  "FAILED" + pause error guard.
