# architecture.md — Project Architecture & Reference

## Overview

**RISC-V Architectural Certification Tests (ACTs)** — generates self-checking assembly tests from CSV testplans, Python generators, and UDB config files. Tests run against a reference model (Sail RISC-V) to compute expected results.

Repository: https://github.com/riscv-non-isa/riscv-arch-test (act4 branch)

## Commands

```bash
make --jobs                          # Generate and compile all tests
make vector-tests                    # Generate vector tests only
FAST=True timeout 60s make coverage   # Isolated coverpoint (60s max)
FAST=True timeout 300s make coverage # Full suite iteration (5 min max)
make clean                           # Remove generated tests AND covergroups (only after fixing a hang)
make clean-tests                     # Remove generated tests only
make CONFIG_FILES=config/duts/cvw/cvw-rv64gc/test_config.yaml EXTENSIONS=I,M,A
make lint / make lint-fix / make format
```

### Incremental Rebuild (no clean needed)

After fixing a testgen script, regenerate and re-run coverage without `make clean`:

```bash
make vector-tests                    # Regenerates .S files (~30s)
rm work/sail-rv64-max/build/rv64i/<Ext>/*.sig   # Delete sigs for affected tests
FAST=True make coverage              # Recompiles elfs (~2 min), re-sims only missing sigs
```

If test content is unchanged (same seed), coverage completes in ~2s. See
`CLAUDE-coverage-workflow.md` for details.

## Pipeline: CSV to ELF

1. CSV testplan maps instructions to coverpoints
2. Coverpoint generators create assembly templates
3. `make vector-tests` invokes covergroupgen + testgen, creates `.S` files
4. UDB config filters applicable tests
5. Sail model runs tests, computes expected results
6. Final self-checking ELFs embedded with expected values

## Directory Structure

```
riscv-arch-test/
├── config/duts/cvw/                              # CVW-specific configs (rv32gc, rv64gc)
├── generators/
│   ├── testgen/src/testgen/coverpoints/          # Coverpoint generator modules (cp_*.py)
│   ├── testgen/scripts/custom/                   # Custom cp_custom_*.py scripts
│   ├── coverage/src/covergroupgen/templates/      # Scalar/general .sv/.txt coverpoint templates
│   │   └── vector/                                # Vector covergroup templates (cmp_*, cp_*, cr_*, sample_*)
│   └── coverage/covergroupgen.py
├── testplans/*.csv                               # Live CSVs (managed by isolation scripts)
├── working-testplans/                            # Canonical CSV source + backups
│   └── duplicates/                               # Canonical backups (Vf-save.csv, etc.)
├── tests/rv32i,rv64i/                            # Generated .S files
├── work/sail-rv64-max/reports/                   # RV64 coverage reports
├── work/sail-rv32-max/reports/                   # RV32 coverage reports
└── isolate_coverpoint.py                         # CSV isolation tool (repo root)
```

## Known Deviations from Upstream

### `-DRVTEST_SELFCHECK` disabled in coverage builds

`build_plan.py` compiles `final.elf` without `-DRVTEST_SELFCHECK`. Coverage runs are unchecked (store-only). Correctness verified separately via RVVI lock-step.

### `RVTEST_SIGUPD` 6-arg API

Upstream added a 6th argument `_STR_PTR`. Vector testgen updated `writeSIGUPD`/`writeSIGUPD_F` accordingly. If builds break with "macro requires 6 arguments but only 5 given", check those functions.

## Python Environment

- Tool: `uv`; Location: `.venv/`; Python 3.12+
- Always invoke via `uv` to ensure correct environment
