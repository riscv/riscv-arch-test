# ACT Configuration for the VeeR EH1 Core

[VeeR EH1](https://github.com/chipsalliance/Cores-VeeR-EH1) is a 32-bit RISC-V core from CHIPS
Alliance. The configuration is pinned to commit `d04b1c7a` and runs the core under Verilator.

| Config     | ISA                          | Modes  |
| ---------- | ---------------------------- | ------ |
| `veer-eh1` | RV32IMC_Zicsr_Zifencei_Zihpm | M only |

- No A, no bit-manipulation, no U-mode, no PMP.

## Building and running

```bash
git clone https://github.com/chipsalliance/Cores-VeeR-EH1 ~/repos/Cores-VeeR-EH1
mkdir -p ~/repos/veer-builds/eh1 && cd ~/repos/veer-builds/eh1
RV_ROOT=~/repos/Cores-VeeR-EH1 make -f $RV_ROOT/tools/Makefile verilator-build

export PATH=$HOME/repos/veer-builds/bin:$PATH   # holds run-veer.sh
export VEER_SNAPSHOT=$HOME/repos/veer-builds/eh1
cd <act root>
make CONFIG_FILES=config/cores/veer-eh1/veer-eh1-rv32imc/test_config.yaml --jobs $(nproc)
./run_tests.py "run-veer.sh --elf" work/veer-eh1-rv32imc/elfs
```

## Platform

- The testbench reset vector is 0. Tests are linked at `TEST_BASE = 0x1000`, and `run-veer.sh`
  prepends a two-instruction boot stub at 0.
