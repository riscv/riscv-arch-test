<!--
Copyright (c) 2026, Harvey Mudd College
SPDX-License-Identifier: Apache-2.0
--->

# ACT Configuration for the Ibex Core

[Ibex](https://github.com/lowRISC/ibex) is a small 32-bit RISC-V core from lowRISC, the main
processor in OpenTitan. The configuration runs
[Ibex Simple System](https://github.com/lowRISC/ibex/tree/master/examples/simple_system) under
Verilator, pinned to `lowRISC/ibex` at `e9f5534`. The RTL is the `opentitan` named configuration
with `BaseIsa` set to `RV32I`, and is not patched.

| Config           | ISA                                        | Modes                 |
| ---------------- | ------------------------------------------ | --------------------- |
| `ibex-opentitan` | RV32IMC_Zba_Zbb_Zbc_Zbs_Zbkb_Zbkc_Zbkx_Zcb | M + U, 16 PMP entries |

Ibex implements privileged specification 1.12.

## Building and running

```bash
.github/scripts/install-ibex.sh ~/repos/ibex-builds
export PATH=$HOME/repos/ibex-builds/bin:$PATH
export IBEX_SNAPSHOT=$HOME/repos/ibex-builds/ot-rv32i
make ibex-opentitan
```

The install script builds Verilator and the Ibex simulator and installs the `run-ibex.sh` runner.
The two exports do what `.github/scripts/setup-ibex.sh` does in CI.
