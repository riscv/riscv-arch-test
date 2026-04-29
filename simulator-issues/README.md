# Simulator Issues — Sail / RISC-V Conformance Suite

This directory tracks behaviours where the **Sail RISC-V model** (or the test
framework's interaction with it) deviates from the RISC-V documentation in a
way that prevents automatically generated SsstrictV / vector privileged tests
from reaching the coverage targets they were designed for.

Each issue is documented in the style of an upstream Sail bug report so that
it can be filed verbatim against
[`riscv-isa/sail-riscv`](https://github.com/riscv/sail-riscv) once verified.

## Issues filed

| # | Title | Status | Workaround |
|---|-------|--------|-----------|
| [001](001-mstatus-vs-clobbered-after-vector-trap.md) | `mstatus.VS` not preserved by Sail across illegal-instruction trap raised by a reserved vector encoding | Workaround in framework | Re-prime FS\|VS=Dirty in `writeVecTest` priv epilog before any vector CSR access |
| [002](002-trap-signature-buffer-too-small.md) | Default `TRAP_SIGUPD_COUNT=15000` overflows for SsstrictV (test framework, not Sail) | Workaround in framework | Bumped to 50000 in `tests/env/check_defines.h` |
| [003](003-vstart-ge-vlmax-no-trap.md) | Sail does not raise illegal-instruction for many vector instructions when `vstart >= VLMAX` | Spec-permitted, coverage gap | Coverpoint `cp_ssstrictv_vstart_ge_vlmax` and reduced-LMUL twins are skipped from generator emission |
| [004](004-sail-omits-some-trapping-vector-instructions.md) | Sail trace omits the trapping vector instruction line for many illegal-instruction traps; rvvi adapter therefore can't sample on it | Sail/framework bug | None at testgen layer — limits all `*_off_group` / `*_reserved` cross coverage to ~6-12% per cross |

## How to add a new issue

1. Reproduce on minimal input.
2. Capture the failing instruction, XEPC, mcause, and Sail commit SHA.
3. Quote the spec section that contradicts the observed behaviour.
4. File in this directory as `NNN-short-title.md`, append a row above.
5. Update the relevant `cp_ssstrictv_*.py` generator (or the pruning list in
   `_ssstrictv_helpers.py`) to skip the affected encoding so the build
   reaches 100% coverage on what *can* be tested.
