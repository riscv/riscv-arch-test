<!--
Copyright (c) 2026, Harvey Mudd College
SPDX-License-Identifier: Apache-2.0
--->

# ACT Configuration for the PicoRV32 Core

[PicoRV32](https://github.com/YosysHQ/picorv32) is a size-optimized RV32IMC core from YosysHQ.
The configuration runs the `picorv32_axi` testbench under Verilator at commit `ef203c2`.

| Config             | ISA               | Modes                      |
| ------------------ | ----------------- | -------------------------- |
| `picorv32-rv32imc` | RV32IMC_Zmmul_Zca | Unprivileged only, no CSRs |

PicoRV32 implements no CSRs or privileged state. UDB needs `Sm` to express `MXLEN`, so the
configuration declares `Sm 1.11.0`. `include_priv_tests: False` and an undefined
`STANDARD_SM_SUPPORTED` keep the privileged tests and the CSR boot code out.

## Building and running

`.github/scripts/install-picorv32.sh` builds Verilator and the patched testbench, and installs
`run-picorv32.sh`. Then set up the environment as `.github/scripts/setup-picorv32.sh` does in CI:

```bash
.github/scripts/install-picorv32.sh <dir>
export PICORV32_SNAPSHOT=<dir>
export PATH=<dir>/bin:$PATH
make picorv32-rv32imc
```

## Platform

- The core is built with `COMPRESSED_ISA`, `ENABLE_FAST_MUL`, `ENABLE_DIV`, `CATCH_MISALIGN`,
  `CATCH_ILLINSN` and `ENABLE_IRQ=0`. A misaligned access, an illegal instruction, `ecall` or
  `ebreak` halts the core.
- RAM: 8 MB at `0x0000_0000`, where the core resets and tests start.
- Console: a word write to `0x1000_0000` emits one character.
- Exit: `RVMODEL_HALT_PASS` writes `123456789` to `0x2000_0000` and executes `ebreak`.
  `RVMODEL_HALT_FAIL` executes `ebreak` only.
