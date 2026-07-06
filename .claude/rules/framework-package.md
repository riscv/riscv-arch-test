---
paths:
  - "framework/**"
---

# act Framework Reference

The `act` CLI orchestrates: parse config -> parse UDB -> select tests -> build plan -> execute build (compile, Sail, signatures, self-checking ELF).

## Key Modules

- `act.py` — CLI entry point (Typer)
- `config.py` — Pydantic models for `test_config.yaml`. Validates executables via `shutil.which`. Frozen model.
- `parse_udb_config.py` — UDB YAML -> internal representation
- `select_tests.py` — Matches tests against DUT capabilities. Handles parameter constraints (e.g., `>=16`).
- `build_plan.py` — Constructs DAG of `BuildTask` objects
- `build_types.py` — `BuildTask` + action dataclasses, shared by the executor and cache
- `build.py` — DAG executor using `graphlib.TopologicalSorter` + `ThreadPoolExecutor`
- `build_cache.py` — Content-hash staleness (`BuildCache`); robust against cache-restore mtimes
- `sig_modify.py` — Processes Sail signatures into self-checking data
- `parse_test_constraints.py` — Reads test file YAML headers

## Build System

DAG of `BuildTask` nodes with actions: `SubprocessAction` (shell), `PythonAction` (direct call), `SymlinkAction`. Executor uses `TopologicalSorter` for parallelism.

Staleness is **content-hash based**, not mtime based (`build_cache.BuildCache`). Each task has a "recipe hash" = Merkle hash over source-input content + action/command + dependency recipes; it never reads intermediate outputs. A task is skipped when its outputs exist and the recipe hash matches the stored value in the per-config manifest `work/<config>/.act_build_cache.json`. Consequences:
- A restored work dir (CI cache) with scrambled mtimes does **not** trigger a rebuild.
- `CLEAN_INTERMEDIATES` can delete `work/<config>/build/` without forcing a rebuild of the final ELFs (deliverables are satisfied by recipe hash even when their intermediates are gone; demand-pull only rebuilds intermediates a needed deliverable actually requires). `BuildTask.intermediate` is set (intrinsically) on `build/` outputs in `build_plan`; `BuildCache` treats such a task as disposable only when the run also passes `clean_intermediates`. So a clean run skips rebuilding missing intermediates a satisfied ELF would otherwise pull, while a normal (non-clean) rerun materializes them — leaving satisfied final ELFs untouched in both cases.
- A swapped tool binary at the same path/flags is **not** detected (only the command string is hashed, not binary content).

## fcov Directory

- `disassemble.svh` — Hand-written instruction decoder case statement
- `coverage/RISCV_imported_decode_pkg.svh` — Auto-generated (do not edit)
