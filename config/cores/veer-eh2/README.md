# ACT Configuration for the CHIPS Alliance VeeR EH2 Core

[VeeR EH2](https://github.com/chipsalliance/Cores-VeeR-EH2) is an open-source 32-bit RISC-V core
from CHIPS Alliance, dual-threaded and with an optional A extension. This configuration is written
against a pinned upstream commit, and every UDB and Sail parameter cites the supporting
documentation text plus a permalink to it.

| Config              | ISA                     | Modes               | Pinned commit |
| ------------------- | ----------------------- | ------------------- | ------------- |
| `veer-eh2-rv32imac` | RV32IMAC_Zicsr_Zifencei | M only, single hart | `bd52450b`    |

Atomics are on, which is the default and the maximum ratified feature set. Bit-manipulation is off
because VeeR's Zb* is a 0.94-draft subset rather than ratified B, and the core is built with one
hart because ACT is single-hart. EH2 implements privileged specification 1.11
(`20190608-Priv-MSU-Ratified`), so it is declared `Sm 1.11.0`: `mstatush` arrived in 1.12, and ACT
guards every access to it behind `SM1P12P0_OR_LATER_SUPPORTED`.

**The A extension cannot actually be exercised.** EH2 makes atomic instructions illegal outside the
DCCM, and an ACT image is much larger than the 64 KB DCCM, so the tests run from system memory
where every atomic faults. `Zaamo` and `Zalrsc` are therefore excluded and do not even build; see
`ci.yaml`.

Current results: 110/127. `ci.yaml` records the reason for every excluded suite.

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

`run_cmd.txt` passes `--stub 0x1000`: the EH2 testbench hardcodes the reset vector to 0
(`reset_vector = {`RV_XLEN{1'b0}};`) and ACT cannot link at address 0, so the runner prepends a
two-instruction jump stub at 0.
