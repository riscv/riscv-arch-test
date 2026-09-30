# ACT Configuration for the VeeR EH1 Core

[VeeR EH1](https://github.com/chipsalliance/Cores-VeeR-EH1) is a 32-bit RISC-V core from CHIPS
Alliance. The configuration is pinned to commit `d04b1c7a` and runs the core under Verilator.

| Config     | ISA                    | Modes  |
| ---------- | ---------------------- | ------ |
| `veer-eh1` | RV32IMC_Zicsr_Zifencei | M only |

## Building and running

```bash
.github/scripts/install-veer-eh1.sh <dir>
export PATH=<dir>/bin:$PATH
export VEER_SNAPSHOT=<dir>/eh1
make veer-eh1-rv32imc
```
