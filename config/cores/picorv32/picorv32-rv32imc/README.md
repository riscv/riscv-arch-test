<!--
Copyright (c) 2026, Harvey Mudd College
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

## DUT Configuration for PicoRV32

[PicoRV32](https://github.com/YosysHQ/picorv32) is a size-optimized RV32IMC core from YosysHQ.
This configuration targets the `picorv32_axi` variant built as RV32IMC, which is what
`make test_verilator` builds and what riscv-formal verifies:
`COMPRESSED_ISA=1`, `ENABLE_FAST_MUL=1`, `ENABLE_DIV=1`, `CATCH_MISALIGN=1`, `CATCH_ILLINSN=1`,
`ENABLE_IRQ=0`.

**This is an unprivileged-only configuration.** PicoRV32 implements no CSR instructions and no
privileged state: opcode `1110011` decodes to exactly four things - the fixed
`rdcycle`/`rdcycleh`/`rdinstret`/`rdinstreth` encodings and `ecall`/`ebreak`. There is no
`csrrw`/`csrrs`/`csrrc` path and no `mtvec`, `mepc`, `mcause`, `mtval`, `mscratch` or `mstatus`
anywhere in `picorv32.v`. Interrupt state lives in custom `q0..q3` registers under the `custom0`
opcode, and the README says the scheme "do not follow the RISC-V Privileged ISA specification".

ACT supports this case directly: `STANDARD_SM_SUPPORTED` is left undefined, so the default boot
code touches no CSRs, and `test_config.yaml` sets `include_priv_tests: False`. See
`docs/ctp/src/abstraction.adoc` and the existing `config/spike/spike-RVI20U32` config.

77 tests are selected: I 39, Zca 26, M 8, Zmmul 4. Everything else in ACT is out of reach.

To build the UDB configuration, coverage files and ELFs, run the following from the top of a
working copy of this repo:

```
$ make CONFIG_FILES=config/cores/picorv32/picorv32-rv32imc/test_config.yaml
```

### Running

`.github/scripts/install-picorv32.sh <dir>` clones picorv32 at the pinned commit, applies the
documented `testbench.v` patches, installs the custom Verilator `main()` and verilates the model.
Set `PICORV32_SNAPSHOT=<dir>` and put `<dir>/bin` on `$PATH`, then:

```
$ make picorv32-rv32imc
```

Two properties of picorv32's stock testbench make the patches mandatory rather than convenient:
its memory array is 128 KB against a ~285 KB ACT image, and an out-of-bounds access `$finish`es
with exit status 0; and `testbench.cc` ends in an unconditional `exit(0)` with no cycle limit
under Verilator, so a hang is indistinguishable from a pass. The replacement `main()` returns
0 only when the core traps with the pass token latched, and returns 1, 2 or 3 for a failing
trap, a cycle-limit expiry and an out-of-bounds access respectively.
