# AGENTS.md

## Repo Shape

- This repo implements the ACT4 framework: generated RISC-V architectural certification tests are compiled into self-checking ELFs whose expected signatures come from Sail.
- Python is a `uv` workspace with three packages: `framework/` exposes `act`, `generators/testgen/` exposes `testgen`, and `generators/coverage/` exposes `covergroupgen`.
- `tests/rv32i`, `tests/rv32e`, `tests/rv64i`, `tests/rv64e`, `coverpoints/unpriv`, and `coverpoints/coverage` are generated but checked in. Do not hand-edit them; edit `testplans/`, `generators/`, or templates, then run `make tests` and commit the regenerated output.
- `work/` is build output. `make clean` removes most artifacts but preserves `extensions.txt` and `.validated`.
- Configs live under `config/`. Any config directory with `run_cmd.txt` gets Make run targets for every ancestor directory name, such as `make spike-rv64-max`, `make spike`, or `make cores`.

## Tooling

- Prefer `mise`; `.mise.toml` pins `uv`, Ruby, Bundler, and `prek`. Without `mise`, `make` requires `uv` plus Ruby/Bundler for UDB.
- Use `uv run` or Make targets for Python commands, not bare `python` or `pip`.
- Keep Python 3.10-compatible. CI explicitly rewrites `.python-version` to `3.10` for the oldest-supported-version job, even if local `.python-version` is newer.
- UDB Ruby deps are under `framework/src/act/data/Gemfile*`; first ACT/UDB use may run `bundle install`.
- Python quality gates are `ruff check` and `pyright` from `pyproject.toml`; Ruff line length is 120, Pyright mode is `standard`.
- `.editorconfig` uses 2 spaces generally, 4 spaces for Python, and tabs only for `Makefile` recipes.
- Use `prek`, not a guessed hook runner: `mise run prek-install` installs hooks and `mise run prek` runs all hooks. The hooks also forbid ambiguous `.align`; use `.p2align` or `.balign`.
- New source files need an SPDX license header.

## Commands

- `make help`: list current targets and knobs.
- `make tests`: generate assembly tests and generated coverpoints only; no compiler or Sail run.
- `make tests` regenerates when anything under `generators/testgen/src/` or `testplans/` changes (the stamp depends on them). To force it, `rm work/stamps/testgen.stamp`.
- `make`: generate tests and build ELFs for default `CONFIG_FILES` (`config/spike/spike-rv32-max/test_config.yaml config/spike/spike-rv64-max/test_config.yaml`).
- `CONFIG_FILES=config/cores/<vendor>/<config>/test_config.yaml make`: build one DUT config.
- `EXTENSIONS=I,M,Zifencei make tests` or `EXTENSIONS=I make`: restrict generation/build to suites. `EXCLUDE_EXTENSIONS=Sm make tests` applies a negative filter after `EXTENSIONS`.
- `make spike-rv64-max`, `make spike`, `make qemu-rv32-max`: build ELFs and run configs discovered from `run_cmd.txt`.
- `./run_tests.py "$(cat config/spike/spike-rv64-max/run_cmd.txt)" work/spike-rv64-max/elfs`: rerun already-built ELFs for one config.
- `FAST=True make`: skip objdump for faster ELF builds. `DEBUG=True make EXTENSIONS=<suite>` emits signature objdump, Sail traces, and trap reports. `VERBOSE=True` implies debug and serializes jobs.
- Do not specify `JOBS` or `--jobs` for normal validation; let the project choose parallelism. Use `JOBS=1 make ...` only when debugging a hang or another issue where parallelism seems to be the cause; `make -jN` is also honored.
- `make coverage EXTENSIONS=<suite>`: focused coverage build. Full `make coverage` is expensive and uses `COVERAGE_CONFIG_FILES` (`config/sail/sail-rv64-max` and `sail-rv32-max`).
- Coverage reports land in `work/<config>/reports/<suite>_summary.txt`, `<suite>_report.txt` (every bin with hit counts) and `<suite>_uncovered.txt` (missing bins only).
- `make vector-tests`: run the standalone vector generators. `EXTENSIONS`/`EXCLUDE_EXTENSIONS` only filter unpriv vector generation; priv vector tests are always generated.
- `make lint`, `make lint-fix`, `make format`: Ruff/Pyright checks and formatting.
- Docs builds run from subdirs: `cd docs/ctp && make docker-pull-latest && make -j6` or `cd docs/crd && make docker-pull-latest && make -j6`. They use the `docs/docs-resources` submodule and Docker unless `SKIP_DOCKER=true`.

## Test Generation

- Unprivileged tests are CSV-driven: `testplans/<suite>.csv` plus coverpoint templates under `generators/coverage/src/covergroupgen/templates/` and Python generators under `generators/testgen/src/testgen/coverpoints/`.
- Privileged tests have no CSV input; generators live in `generators/testgen/src/testgen/priv/extensions/`, generated `.S` outputs live under `tests/priv/`, and hand-written coverage lives under `coverpoints/priv/`.
- Test YAML headers are strict. Recognized keys are only `REQUIRED_EXTENSIONS`, `MARCH`, and optional `params`; unknown keys fail validation. Headers use `START_TEST_CONFIG`/`END_TEST_CONFIG` markers before assembly.
- Test terminology matters: a testcase is one coverpoint bin check, a `TestChunk` is an unsplittable group of testcases, a test file is one generated `.S`, and a test suite is the directory/extension group.
- CSV columns: `Instruction`, `Type`, `RV32`, `RV64`, then coverpoints. `Type` must match a registered formatter; coverpoint columns must match registered generators. Use `testplans/I.csv` as the reference shape.
- Registry files are auto-discovered by decorators; do not add manual registration. Files whose names start with `_` are skipped by discovery.

| Subsystem              | Decorator                                    | Directory                                          |
| ---------------------- | -------------------------------------------- | -------------------------------------------------- |
| Coverpoint generators  | `@add_coverpoint_generator("cp_name")`       | `generators/testgen/src/testgen/coverpoints/`      |
| Instruction formatters | `@add_instruction_formatter("TYPE", config)` | `generators/testgen/src/testgen/formatters/types/` |
| Priv test generators   | `@add_priv_test_generator("Suite", ...)`     | `generators/testgen/src/testgen/priv/extensions/`  |

- Do not hand-edit `framework/src/act/fcov/coverage/RISCV_imported_decode_pkg.svh`; it is generated from `riscv-opcodes`.
- Unprivileged tests do not install trap handlers and can infinite-loop on traps. Tests that may trap should use the privileged-test style.
- In privileged generated assembly, avoid loops; emit repeated code with Python loops so testcase labels/debug strings stay unique.
- When modifying Python generators, don't add a lot of stuff to docstrings.
- When changing files, don't leave comments about what was changed or why. Just focus on what it does.

## T-SBI Conversion

- Privileged suites are being converted to T-SBI: the test boots to its own mode and asks the M-mode trap handler (via `ecall`) to perform privileged operations instead of hopping modes. For work involving T-SBI conversion, consult guidelines in `docs/tsbi-changes.md`.

## Configs And CI

- A runnable config directory needs `test_config.yaml`, UDB YAML, `rvmodel_macros.h`, `link.ld`, `sail.json`, `rvtest_config.h`, and `rvtest_config.svh`. Paths in `test_config.yaml` are relative to that file.
- Linker scripts must keep `.text.rvmodel` after `.data`; otherwise DUT and reference-model ELFs can disagree on data addresses. If the ELF base address changes, update the Sail memory map in `sail.json`.
- `run_cmd.txt` contains one shell command; `run_tests.py` appends the ELF path. Use `{debug:...}` for debug-only simulator flags, `__TRACEFILE__` for separate trace logs, and `__SUMMARYFILE__` when console summaries must be redirected away from trace output.
- CI matrix discovery uses `config/*/ci.yaml` plus each `run_cmd.txt`. Run `make tests` before `.github/scripts/ci_config.py`; generated tests are used to weight shards.
- CI checks that generated files (`tests/rv32i tests/rv32e tests/rv64i tests/rv64e coverpoints/unpriv coverpoints/coverage`) have not changed.
- PRs branch from and target `act4`; docs release workflow also triggers from `act4`.

## Debugging

- Per-config run summaries are in `work/<config>/summary.log`; per-test simulator logs are in `work/<config>/logs/`.
- Passing tests print lines matching `RVCP-SUMMARY: TEST PASSED - Test File "<test_name.S>"`; failures use `TEST FAILED`. `SIGRUN` means the ELF was not built self-checking.
- With `DEBUG=True`, ACT build artifacts in `work/<config>/build/` include `.sig.log` Sail traces and `.sig.trap_report` files.
- Triage failures in this order: config/UDB mismatch, Sail config mismatch, generated objdump/trace, then DUT behavior.
- To measure one suite everywhere: `EXTENSIONS=<suite> DEBUG=True make -k sail spike whisper qemu imperas cvw`. `DEBUG=True` keeps a trace per test; `make -k` continues past a failing config. Each failing test's `.log` names the first diverging testcase on its `bin:` line.
- Ghost outputs: nothing cleans `tests/priv/<suite>/` or `work/<config>/elfs/priv/<suite>/`, so a renamed or retired chunk keeps being built, run, and counted, and `run_tests.py`'s "N tests" includes it. When chunk names change, delete the stale files by name — not by mtime, since unchanged files keep their old timestamps.
