<!--
Copyright (c) 2026, Harvey Mudd College
SPDX-License-Identifier: Apache-2.0
-->

# ACT Configuration for the CHIPS Alliance VeeR EH2 Core

[VeeR EH2](https://github.com/chipsalliance/Cores-VeeR-EH2) is a dual-threaded 32-bit RISC-V core
from CHIPS Alliance. The configuration runs the RTL under Verilator, pinned to commit `a7203d02`.

| Config               | ISA                                                    | Modes               |
| -------------------- | ------------------------------------------------------ | ------------------- |
| `veer-eh2-rv32imacb` | RV32IMAC_Zicsr_Zifencei_Zba_Zbb_Zbc_Zbs_Zbkb_Zbkc_Zbkx | M only, single hart |

The core is built with `atomic_enable=1`, `num_threads=1`, `dccm_size=256`, and every `bitmanip_*`
option set to 1. EH2 executes AMOs and LR/SC only in the DCCM, so `link.ld` places the test `.data`
section there; the DCCM is enlarged from the default 64 KB because some tests' `.data` exceeds 64 KB.

## Building and running

`install-veer-eh2.sh` builds Verilator and the core and installs `run-veer-eh2.sh`. Then set the
two variables that `setup-veer-eh2.sh` sets in CI and run the configuration:

```bash
.github/scripts/install-veer-eh2.sh $HOME/veer-eh2
export PATH=$HOME/veer-eh2/bin:$PATH
export VEER_SNAPSHOT=$HOME/veer-eh2/eh2
make veer-eh2-rv32imacb
```
