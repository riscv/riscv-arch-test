# CHANGELOG

## [4.0.0] - 2026-04-16

### Overview

ACT 4.0 is a major overhaul of the RISC-V Architecture Certification Test suite. The old `riscof`/`riscv-ctg`/`riscv-isac`/`riscv-config` flow has been replaced with an entirely new Python-based test compilation framework, a new `testgen` package for generating tests, and SystemVerilog-based functional coverage. The tests are now self-checking and many more RISC-V extensions are now supported.

### Details

- Complete rewrite of the test framework, replacing `riscof`/`riscv-ctg`/`riscv-isac` with a new Python-based system
- Custom Python build system, replacing generated Makefiles from `riscof`
- Configuration validation driven by [RISC-V Unified Database (UDB)](https://github.com/riscv/riscv-unified-db)
- All tests are now self-checking and report pass/fail status without post-processing using expected results from the [RISC-V Sail model](https://github.com/riscv/sail-riscv)
  - Detailed failure logging with failing instructions, expected result, and mismatched actual result
- Coverage collection using industry-standard SystemVerilog functional coverage with coverpoints linked to normative rules from the [ISA manual](https://docs.riscv.org/reference/isa/unpriv/intro.html)
- The [Certification Test Plan (CTP)](https://riscv.github.io/riscv-arch-test/ctp.html) contains details on what features each test and coverpoint exercise
- The ACT4 tests have been validated on the Spike, QEMU, and Whisper simulators

## Previous Versions

For release notes of previous versions of the riscv-arch-test suite (3.10 and earlier) see [the previous changelog](https://github.com/riscv/riscv-arch-test/blob/old-framework-3.x/CHANGELOG.md).
