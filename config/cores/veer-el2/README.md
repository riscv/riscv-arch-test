# ACT Configuration for the CHIPS Alliance VeeR EL2 Core

[VeeR EL2](https://github.com/chipsalliance/Cores-VeeR-EL2) is an open-source 32-bit RISC-V core
from CHIPS Alliance. This configuration is written against a pinned upstream commit, and every UDB
and Sail parameter cites the supporting documentation text plus a permalink to it.

| Config | ISA | Modes | Pinned commit |
|---|---|---|---|
| `veer-el2-rv32imc-u-pmp` | RV32IMC_Zicsr_Zifencei | M + U, 64 PMP entries | `925f3a34` |

EL2's U-mode and PMP are both optional and are enabled here at their maximum, which is its maximum
ratified feature set. Its bit-manipulation is a 0.94-draft subset rather than ratified B, so the
RTL is built with those knobs off, and Smepmp is left disabled.

VeeR EL2 implements privileged specification 1.11 (`20190608-Priv-MSU-Ratified`), so it is declared
`Sm 1.11.0`. That matters: `mstatush` arrived in 1.12, and ACT guards every access to it behind
`SM1P12P0_OR_LATER_SUPPORTED`.

Current results: 158/190. `ci.yaml` records the reason for every excluded suite.

## Building and running

```bash
# once: verilate the core (see .github/scripts/install-veer-el2.sh for the exact command)
git clone https://github.com/chipsalliance/Cores-VeeR-EL2 ~/repos/Cores-VeeR-EL2
mkdir -p ~/repos/veer-builds/el2 && cd ~/repos/veer-builds/el2
RV_ROOT=~/repos/Cores-VeeR-EL2 make -f $RV_ROOT/tools/Makefile verilator-build \
  CONF_PARAMS='-set build_axi4 -set user_mode=1 -set pmp_entries=64 -set smepmp=0 \
               -set bitmanip_zba=0 -set bitmanip_zbb=0 -set bitmanip_zbc=0 -set bitmanip_zbs=0 \
               -set fast_interrupt_redirect=0'

# build and run the tests
export PATH=$HOME/repos/veer-builds/bin:$PATH   # holds run-veer-el2.sh
export VEER_SNAPSHOT=$HOME/repos/veer-builds/el2
cd <act root>
make CONFIG_FILES=config/cores/veer-el2/veer-el2-rv32imc-u-pmp/test_config.yaml --jobs $(nproc)
./run_tests.py "run-veer-el2.sh --elf" work/veer-el2-rv32imc-u-pmp/elfs
```

`fast_interrupt_redirect` must be off: with the default, external interrupts vector through the
`meivt` table instead of `mtvec` and never reach the ACT trap handler.

The tests link at `0x8000_0000`, the reset vector the EL2 testbench takes from `RV_RESET_VEC`, so
no boot stub is needed.
