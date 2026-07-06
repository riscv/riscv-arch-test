# AGENTS.md

Canonical instructions for **any** AI coding agent working in this repository
(Codex, Cursor, GitHub Copilot, Gemini, Claude, etc.).

This is the single source of truth. Agent-specific entry points are thin
pointers to this file so every agent reads the same guidance.

**When you update guidance, edit `AGENTS.md` only.** The others are symlinks and
update automatically.

@RTK.md

# OpenWolf

@.wolf/OPENWOLF.md

This project uses OpenWolf for context management. Read and follow .wolf/OPENWOLF.md every session. Check .wolf/cerebrum.md before generating code. Check .wolf/anatomy.md before reading files.

# Caveman final summary

When caveman mode active: keep caveman style during working turns (analysis, intermediate replies, tool narration), but write the final wrap-up summary — the "here's what I did" message — in normal, full English. Resume caveman next working turn.

## Overview

This is the RISC-V Architectural Certification Tests (ACTs) repository implementing the **ACT4 Framework** — a Python tool for generating, compiling, and running self-checking ELF tests that certify RISC-V implementations against the ISA specification. Tests are generated from CSV testplans and compiled using the RISC-V Sail reference model to compute expected results.

## Common Commands

All commands run from the repo root. The framework uses `mise` to manage tool dependencies (Ruby/UDB and Python/uv).

```bash
# Generate assembly tests (no compiler/Sail needed)
make tests

# Generate and compile self-checking ELFs for default configs (spike rv32/rv64)
make

# Run with a specific DUT config
CONFIG_FILES=config/cores/<vendor>/<config>/test_config.yaml make

# Run tests on Spike simulator
make spike            # all spike configs
make spike-rv32-max   # single config (targets auto-generated from config/<sim>/<name>/)
make spike-rv64-max   # available: spike-{rv32-max,rv64-max,RVI20U32,RVI20U64}, qemu-*

# Per-config results: work/<config>/summary.log (grep for PASSED/FAILED)

# Force regeneration after touching generators (stamps otherwise short-circuit)
make clean-tests && make tests

# Lint and type-check Python
make lint          # ruff check + pyright
make lint-fix      # ruff check --fix
make format        # ruff format

# Clean build artifacts (preserves extensions.txt)
make clean

# Clean generated test sources
make clean-tests

# Limit test generation to specific extensions
EXTENSIONS=I,M,Zifencei make tests

# Exclude specific extensions
EXCLUDE_EXTENSIONS=ExceptionsSm make tests

# Coverage generation (generates SystemVerilog fcov reports)
make coverage
```

## Git Workflow

PRs target the `act4` branch (not `dev` or `main`). Use a separate feature branch per change. PRs are squash-merged.

## Tool Management

- **Tool manager**: `mise` — manages both Ruby (for UDB) and uv/Python. Config in `.mise.toml`.
- **Ruby**: 3.2+ (for the `udb` gem). Dependencies locked in `Gemfile` / `Gemfile.lock`. Auto-installed by the `act` package when first needed via `bundle install`.
- **Python**: `uv` (fast Python package manager); venv at `.venv/` (auto-managed). Always use `uv run` to execute Python scripts or tools — never invoke `python` directly.
- **Python version**: 3.10+
- **Key Python packages**: pydantic, pyjson5, ruamel-yaml, typer

## Python Project Structure

A `uv` workspace with three packages (defined in the top-level `pyproject.toml`):

- **`framework/`** (`act` package) — The ACT4 framework CLI. Entry point: `act`.
- **`generators/testgen/`** (`testgen` package) — CLI (`testgen`) that reads CSV testplans and generates RISC-V assembly test files.
- **`generators/coverage/`** (`covergroupgen` package) — Generates `.svh` covergroup files from SystemVerilog templates.

Additionally, **`generators/ctp/`** contains standalone scripts for CTP documentation generation (PEP 723 inline metadata, run with `uv run`).

## Architecture and Data Flow

### Privileged vs. Unprivileged Tests

- **Unprivileged**: CSV-driven. `testplans/<EXT>.csv` → `testgen` → `.S` files in `tests/rv{32,64}{i,e}/`. Vector extensions use EFFEW expansion (e.g., `Vx.csv` → `Vx8`, `Vx16`, `Vx32`, `Vx64`).
- **Privileged**: No CSV. Python generators in `generators/testgen/src/testgen/priv/extensions/` → `tests/priv/`.
- **No-signature tests**: a test header may set `NEEDS_SIGNATURE: false` (optional key, defaults to true) to skip the signature/reference-model pipeline and compile directly to the final ELF. Coverage traces still work (the final ELF runs on Sail like any other test). Intended for fully self-checking tests: all handwritten C tests (required — validation errors otherwise) and, in the future, self-checking `.S` tests.
- **Handwritten C tests** (e.g. Breker TREK in `tests/trek/Trek/`): self-checking `.c` files with the standard YAML test-config header (including `NEEDS_SIGNATURE: false`) inside a `/* ... */` block comment. Discovered like `.S` tests (any `tests/**/<Suite>/*.c`); compiled once directly to an ELF with the shared runtime in `tests/env/` (`c_test_start.S`, `c_test_support.c`). `main()` returning 0 reports PASS; nonzero or `trek_error()` reports FAIL. All DUT interfacing goes through the config's `RVMODEL_*` macros; per-hart stacks and `.bss` come from the config `link.ld`. Prototypes for tests: `tests/env/c_test.h`.

### Terminology Hierarchy

Do not confuse these terms:

- **testcase**: Smallest unit — individual test checking a single bin of a coverpoint.
- **test chunk** (`TestChunk`): Unsplittable group of testcases — building block of test files.
- **test file**: A complete `.S` file compiled into an ELF, made of one or more test chunks.
- **test suite**: All test files in a given directory (one extension/feature).

### Generated vs. Hand-Written Files

Never manually edit generated files — they are overwritten by `make tests`. See `.claude/rules/generated-files.md` for the full list and where to edit instead.

### Registry/Decorator Pattern

The codebase uses a consistent auto-discovery registry pattern across three subsystems:

| Subsystem              | Decorator                                    | Auto-discovered Directory                        |
| ---------------------- | -------------------------------------------- | ------------------------------------------------ |
| Coverpoint generators  | `@add_coverpoint_generator("cp_name")`       | `testgen/coverpoints/` (+ `special/`, `vector/`) |
| Instruction formatters | `@add_instruction_formatter("TYPE", config)` | `testgen/formatters/types/`                      |
| Priv test generators   | `@add_priv_test_generator("Suite", ...)`     | `testgen/priv/extensions/`                       |

Files are auto-imported via `discover_and_import_modules()`. Files starting with `_` are skipped. No manual registration needed. Use the agents in `.claude/agents/` for step-by-step workflows.

### Testplan CSV Format

```csv
Instruction,Type,RV32,RV64,cp_asm_count,cp_rs1,cp_rs2,cp_rd,...
add,R,x,x,x,x,x,x,...
addi,I,x,x,x,x,,x,...
```

- Mark XLEN support with `x`. Mark applicable coverpoints with `x` (or variant suffix like `20bit`).
- `cp_*` — single-variable coverpoints. `cr_*` — cross-coverage. `cmp_*` — register comparisons. `cp_custom*` — special/custom.
- `Type` must match a registered instruction formatter. Coverpoint columns must match a registered generator.
- See `testplans/I.csv` for a complete reference.

## Test Output and Debugging

- **PASSED**: `RVCP-SUMMARY: Test File "<test_name.S>": PASSED`
- **FAILED**: `RVCP-SUMMARY: Test File "<test_name.S>": FAILED`

**Triage order**: config mismatch → Sail config → objdump → DUT bug.

## Common Pitfalls

- **Editing generated files**: Edit generators instead.
- **Terminology confusion**: "testcase" is a single bin check, not a file.
- **Missing SPDX header**: Every new source file needs `# SPDX-License-Identifier: Apache-2.0`.
- **Forgetting `make lint`**: Always run before committing. ruff + pyright must both pass.
- **Wrong PR target**: PRs go to `act4`, not `dev` or `main`.
- **Using `python` directly**: Always use `uv run` instead.
- **Large generated `.S` files exceed the editor read limit**: read in ranges (offset/limit) or use `grep` (e.g. `F-feq.s-00.S` is ~1 MB).
- **PMP encoding across config files** (UDB yaml vs `sail.json` vs `whisper.json`). The three files use _different_ encodings of the PMP granularity and they must all agree:
  - UDB yaml `PMP_GRANULARITY` = `log2(granularity_in_bytes)` (i.e. **spec G + 2**). E.g. 4KB minimum → `PMP_GRANULARITY: 12`. This is what test sources see as `UDB_PMP_GRANULARITY`.
  - `sail.json` `pmp.grain` = spec G (granularity = `2^(G+2)` bytes). Same 4KB → `"grain": 10`.
  - `whisper.json` `physical_memory_protection_grain` = granularity in bytes. Same 4KB → `"0x1000"`.
  - Also keep `NUM_PMP_ENTRIES` (yaml) ↔ `pmp.count` (sail.json) in sync. If UDB `NUM_PMP_ENTRIES: 0` but `sail.json` `pmp.count > 0`, `tests/env/rvtest_setup.h` skips the PMP-allow-all setup and S/U fetches trap-loop.
  - When the simulator config files disagree on the canonical granularity, treat the actual simulator config (e.g. `whisper.json`) as the source of truth and adjust the UDB yaml + `sail.json` to match — _not_ the reverse.

## Maintaining These Instructions

Keep instructions up to date. Whenever you learn something new about this
codebase, make a mistake better instructions would have prevented, or discover a
pattern worth documenting, update the right place:

- **`AGENTS.md`** (this file) — project overview, architecture, commands, pitfalls. Shared by all agents.
- **`.claude/rules/`** — path-scoped conventions and package references (Claude Code; Cursor analog: `.cursor/rules/`, Copilot: `.github/instructions/`).
- **`.claude/agents/`** — step-by-step workflows for common development tasks.
- **`.claude/skills/`** — repeatable commands (`/lint-fix`, `/gen-tests`, `/verify-ext`).
- **`.claude/hooks/`** — automated guards and formatters.

If you hit a pitfall, add it to **Common Pitfalls**. If a convention prevented a
mistake, it is working — if it did not, improve it.

## Contributing

See `CONTRIBUTING.md` for full details. Key points:

- `make lint` must pass
- Add `# SPDX-License-Identifier: Apache-2.0` to new files
- Pre-commit hooks are configured: `pre-commit run --all-files`
