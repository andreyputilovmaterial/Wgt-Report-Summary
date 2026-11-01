# Design principles

- **Simplicity and predictability.** The tool is a pure input -> output transform:
  give it a report (or reports), get a CSV. Avoid conditional "modes" or
  orchestration logic (scanning, recency filtering, etc.) inside the Python script;
  that belongs in the wrapper `.bat`/shell scripts.
- Modularity: Prefer self-contained, cohesive components with clearly defined inputs and outputs.
- Testing: Accompany new features and behavioral changes with appropriate automated tests.
- Dependencies: Avoid unnecessary dependencies.
- Consistency: Follow existing project conventions and avoid unrelated changes.
