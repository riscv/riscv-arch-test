<!--
Copyright (c) 2026, Harvey Mudd College
SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
--->

# ACT Configuration for the PicoRV32 Core

[PicoRV32](https://github.com/YosysHQ/picorv32) is a size-optimized RV32IMC core from YosysHQ.
The configuration runs the `picorv32_axi` variant under Verilator 5.036, pinned to commit
`ef203c2`.

| Config             | ISA               | Modes                      |
| ------------------ | ----------------- | -------------------------- |
| `picorv32-rv32imc` | RV32IMC_Zmmul_Zca | Unprivileged only, no CSRs |

- No CSR instructions and no privileged state: opcode `1110011` decodes only the fixed
  `rdcycle`/`rdcycleh`/`rdinstret`/`rdinstreth` encodings and `ecall`/`ebreak`.
- `Zicsr`, `Zicntr` and `Zifencei` are not claimed; `fence.i` is an illegal instruction.
- `Sm 1.11.0` is declared only so UDB can express `MXLEN`; `include_priv_tests: False` and an
  undefined `STANDARD_SM_SUPPORTED` keep all privileged tests and CSR boot code out.
- `MISALIGNED_LDST: false`: a misaligned access halts the core (`CATCH_MISALIGN=1`).

## RTL configuration

`.github/scripts/install-picorv32.sh` patches `testbench.v` (not `picorv32.v`) and replaces
`testbench.cc`:

- `COMPRESSED_ISA`, `ENABLE_FAST_MUL=1`, `ENABLE_DIV=1`, `CATCH_MISALIGN=1`, `CATCH_ILLINSN=1`.
- `ENABLE_IRQ=0`, so `ecall`/`ebreak`/illegal instructions drive `trap`.
- `PROGADDR_RESET = 0x0000_4000`.
- Memory raised from 128 KB to 8 MB.
- `tests_passed` exposed as a top-level port; the failing-trap `$stop` changed to `$finish`.
- Custom `main()` exits 0 on a trap with the pass token latched, and 1, 2 or 3 on a failing trap,
  a cycle-limit expiry or an out-of-bounds access.

## Building and running

```bash
.github/scripts/install-picorv32.sh <dir>
export PICORV32_SNAPSHOT=<dir>
export PATH=<dir>/bin:$PATH
make CONFIG_FILES=config/cores/picorv32/picorv32-rv32imc/test_config.yaml
make picorv32-rv32imc
```

## Platform

- RAM: 8 MB at `0x0000_0000`; tests start at `0x0000_4000`.
- Console: a word write to `0x1000_0000` emits one character.
- Exit: `RVMODEL_HALT_PASS` writes `123456789` to `0x2000_0000` and executes `ebreak`;
  `RVMODEL_HALT_FAIL` executes `ebreak` only.
- `RVMODEL_BOOT` and `RVMODEL_ACCESS_FAULT_ADDRESS` are undefined; the core raises no access
  faults.
