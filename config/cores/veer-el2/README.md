# ACT Configuration for the VeeR EL2 Core

[VeeR EL2](https://github.com/chipsalliance/Cores-VeeR-EL2) is a 32-bit RISC-V core from CHIPS
Alliance. The configuration runs the RTL under Verilator, pinned to commit `925f3a34`.

| Config                   | ISA                    | Modes                 |
| ------------------------ | ---------------------- | --------------------- |
| `veer-el2-rv32imc-u-pmp` | RV32IMC_Zicsr_Zifencei | M + U, 64 PMP entries |

- Privileged specification 1.11 (`Sm 1.11.0`); no `mstatush`.
- Bit-manipulation is a 0.94-draft subset, not ratified B, and is not claimed.
- Smepmp is not claimed.
- `Zihpm` is claimed; only `hpmcounter3..6` are implemented.

## RTL configuration

`.github/scripts/install-veer-el2.sh` builds with these deviations from the upstream defaults:

- `user_mode=1`, `pmp_entries=64`: U-mode and PMP at their maximum.
- `smepmp=0`.
- `bitmanip_zba=0`, `bitmanip_zbb=0`, `bitmanip_zbc=0`, `bitmanip_zbs=0`.
- `fast_interrupt_redirect=0`: otherwise external interrupts vector through `meivt` instead of
  `mtvec`.

## Building and running

```bash
git clone https://github.com/chipsalliance/Cores-VeeR-EL2 ~/repos/Cores-VeeR-EL2
mkdir -p ~/repos/veer-builds/el2 && cd ~/repos/veer-builds/el2
RV_ROOT=~/repos/Cores-VeeR-EL2 make -f $RV_ROOT/tools/Makefile verilator-build \
  CONF_PARAMS='-set build_axi4 -set user_mode=1 -set pmp_entries=64 -set smepmp=0 \
               -set bitmanip_zba=0 -set bitmanip_zbb=0 -set bitmanip_zbc=0 -set bitmanip_zbs=0 \
               -set fast_interrupt_redirect=0'

export PATH=$HOME/repos/veer-builds/bin:$PATH   # holds run-veer-el2.sh
export VEER_SNAPSHOT=$HOME/repos/veer-builds/el2
make CONFIG_FILES=config/cores/veer-el2/veer-el2-rv32imc-u-pmp/test_config.yaml --jobs $(nproc)
./run_tests.py "run-veer-el2.sh --elf" work/veer-el2-rv32imc-u-pmp/elfs
```

## Platform

- Tests link at `0x8000_0000`, the testbench reset vector (`RV_RESET_VEC`); no boot stub.
