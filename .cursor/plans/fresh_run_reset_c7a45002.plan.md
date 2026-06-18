---
name: Fresh run reset
overview: Add a reusable CLI reset capability (a `folk reset` command plus a `run --fresh` flag) that wipes the SQLite DB tables, the resume checkpoint, and stale output report files, so a full `python -m folk.cli run` reprocesses all 197 countries from scratch with no carryover.
todos:
  - id: reset-helper
    content: Add _reset_state(repos, clean_outputs) helper in cli.py that drops+recreates DB tables and deletes stale folk_* output artifacts
    status: completed
  - id: reset-cmd
    content: Add _cmd_reset and a `reset` subparser (with --keep-outputs) in build_parser()
    status: completed
  - id: fresh-flag
    content: Add --fresh flag to the run subparser and invoke _reset_state before pipeline.run in _cmd_run
    status: completed
  - id: verify
    content: "Smoke-test: run `folk reset` then confirm DB/outputs cleared; verify `run --fresh` parses"
    status: completed
isProject: false
---

## Root cause (confirmed)

A subset run only *processes* the requested ISOs, but the report is rebuilt from the whole DB:

- `Pipeline.run` filters records to `--isos`, so only KOR + DEU were scored ([src/folk/pipeline/pipeline.py](src/folk/pipeline/pipeline.py) lines 72-76).
- `Pipeline.finalize` aggregates `self.repos.profiles.all()` — every profile already in `outputs/folk.sqlite` (87 from prior runs) ([src/folk/pipeline/pipeline.py](src/folk/pipeline/pipeline.py) lines 158-167).
- `Exporter` likewise dumps `self.repos.profiles.all()` for all artifacts ([src/folk/export/exporter.py](src/folk/export/exporter.py)).

So the only thing needed for a clean full run is to wipe the persisted state. The DB already exposes `drop_all()` / `create_all()` ([src/folk/storage/db.py](src/folk/storage/db.py) lines 31-35), which clears profiles, references, validations, audits, evidence, and the `processed_isos` checkpoint in one shot.

## Changes

### 1. Add a reset helper
In [src/folk/cli.py](src/folk/cli.py), add a module-level `_reset_state(repos, clean_outputs=True)` that:
- Calls `repos.db.drop_all()` then `repos.db.create_all()` (clears all tables incl. checkpoint; avoids Windows file-lock issues vs deleting the `.sqlite` file).
- When `clean_outputs`, deletes stale report artifacts in `settings.outputs_dir` via glob (`folk_*.json`, `folk_*.xlsx`, `folk_*.txt`, `folk_run_log.jsonl`) so old 87-country reports don't linger. Leaves `folk.sqlite` (now empty) and input logs intact.

### 2. New `reset` subcommand
Add `_cmd_reset` + a `reset` subparser in `build_parser()`. It instantiates `Repositories()` directly (cheap; no Excel/LLM needed), runs `_reset_state`, and logs what was cleared. Optional `--keep-outputs` flag to wipe DB only.

### 3. `run --fresh` flag
Add `--fresh` to the `run` subparser. In `_cmd_run`, when set, call `_reset_state(pipeline.repos)` immediately after `Pipeline()` is constructed and before `pipeline.run(...)`, guaranteeing a from-scratch full run in one command.

## Usage after change
- Clean everything, then full run:
  - `python -m folk.cli reset`
  - `python -m folk.cli run`
- Or one-shot: `python -m folk.cli run --fresh`

## Notes / non-goals
- Subset-run reporting behavior is intentionally left as-is (reports reflect the whole DB), per your choice.
- `_reset_state` uses `drop_all`+`create_all` rather than file deletion to dodge SQLite file locks on Windows.