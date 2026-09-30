# ACT Configuration for the CHIPS Alliance VeeR EH2 Core

[VeeR EH2](https://github.com/chipsalliance/Cores-VeeR-EH2) is a dual-threaded 32-bit RISC-V core
from CHIPS Alliance. The configuration runs the RTL under Verilator, pinned to commit `a7203d02`.

| Config              | ISA                     | Modes               |
| ------------------- | ----------------------- | ------------------- |
| `veer-eh2-rv32imac` | RV32IMAC_Zicsr_Zifencei | M only, single hart |

- Privileged specification 1.11 (`Sm 1.11.0`); no `mstatush`.
- A/Zaamo/Zalrsc are claimed, but atomic instructions are illegal outside the 64 KB DCCM and ACT
  images run from system memory, so the `Zaamo` and `Zalrsc` suites are excluded.
- Bit-manipulation is not claimed: VeeR's Zb\* is a 0.94-draft subset, not ratified B.

## RTL configuration

`atomic_enable=1` (the default), `num_threads=1`, and all `bitmanip_*` options set to 0.

## Building and running

```bash
# once: verilate the core (see .github/scripts/install-veer-eh2.sh for the exact command)
git clone https://github.com/chipsalliance/Cores-VeeR-EH2 ~/repos/Cores-VeeR-EH2
mkdir -p ~/repos/veer-builds/eh2 && cd ~/repos/veer-builds/eh2
RV_ROOT=~/repos/Cores-VeeR-EH2 make -f $RV_ROOT/tools/Makefile verilator-build \
  CONF_PARAMS='-set atomic_enable=1 -set num_threads=1 -set bitmanip_zba=0 -set bitmanip_zbb=0 \
               -set bitmanip_zbc=0 -set bitmanip_zbs=0 -set bitmanip_zbkb=0 -set bitmanip_zbkx=0'

# build and run the tests
export PATH=$HOME/repos/veer-builds/bin:$PATH   # holds run-veer-eh2.sh
export VEER_SNAPSHOT=$HOME/repos/veer-builds/eh2
cd <act root>
make CONFIG_FILES=config/cores/veer-eh2/veer-eh2-rv32imac/test_config.yaml --jobs $(nproc)
./run_tests.py "run-veer-eh2.sh --stub 0x1000 --elf" work/veer-eh2-rv32imac/elfs
```

## Platform

- The testbench hardcodes the reset vector to 0, where ACT cannot link; `run_cmd.txt` passes
  `--stub 0x1000` so the runner places a two-instruction jump stub at 0.
