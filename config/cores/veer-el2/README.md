<!--
Copyright (c) 2026, Harvey Mudd College
SPDX-License-Identifier: Apache-2.0
-->

# ACT Configuration for the VeeR EL2 Core

[VeeR EL2](https://github.com/chipsalliance/Cores-VeeR-EL2) is a 32-bit RISC-V core from CHIPS
Alliance. The configuration runs the RTL under Verilator.

| Config                    | ISA                                         | Modes                 |
| ------------------------- | ------------------------------------------- | --------------------- |
| `veer-el2-rv32imcb-u-pmp` | RV32IMC_Zicsr_Zifencei_Zba_Zbb_Zbc_Zbs_Zbkc | M + U, 64 PMP entries |

- Privileged specification 1.11 (`Sm 1.11.0`).
- `Zihpm` with `hpmcounter3..6`.

## RTL configuration

`.github/scripts/install-veer-el2.sh` builds commit `925f3a34` with these options:

- `user_mode=1`, `pmp_entries=64`: U-mode and the largest PMP.
- `smepmp=0`, the default.
- `bitmanip_zba=1`, `bitmanip_zbb=1`, `bitmanip_zbc=1`, `bitmanip_zbs=1`, the default. The draft
  Zbe, Zbf, Zbp and Zbr stay off.
- `fast_interrupt_redirect=0`: otherwise external interrupts vector through `meivt` instead of
  `mtvec`.

## Building and running

The install script builds Verilator and the VeeR EL2 testbench and installs `run-veer-el2.sh`.
The two exports do what `.github/scripts/setup-veer-el2.sh` does in CI.

```bash
.github/scripts/install-veer-el2.sh $HOME/veer-el2
export PATH=$HOME/veer-el2/bin:$PATH
export VEER_SNAPSHOT=$HOME/veer-el2/el2
make veer-el2-rv32imcb-u-pmp
```
