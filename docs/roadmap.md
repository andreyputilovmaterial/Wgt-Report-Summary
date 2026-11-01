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
