# Configuration & Tuning

This prototype does not yet include a full `config.yaml`, but here are recommended configuration options and where to put them when implemented.

Suggested fields:

- `monitor`
  - `interval`: float seconds between clipboard polls (default 0.6)
  - `enabled`: boolean
- `detection`
  - `patterns`: path to `patterns/regex_patterns.py` or inline regex set
  - `entropy_threshold`: float (example: 4.5)
- `response`
  - `auto_clear`: mapping of risk -> bool
  - `alert_delay`: seconds before clearing (for High risk)
- `storage`
  - `history_enabled`: bool
  - `db_path`: path to sqlite DB

Place a `config.yaml` in the repository root and load it with `PyYAML` / `pydantic` when implementing `monitor.py`.
