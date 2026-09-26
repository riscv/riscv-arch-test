# ACT Configuration for the CHIPS Alliance VeeR EH1 Core

[VeeR](https://github.com/chipsalliance) is a family of open-source RISC-V cores from CHIPS
Alliance. Configurations here are written against a pinned upstream commit, and every UDB and Sail
parameter cites the supporting documentation text plus a permalink to it.

| Config     | Core                                                        | ISA                          | Modes  | Pinned commit |
| ---------- | ----------------------------------------------------------- | ---------------------------- | ------ | ------------- |
| `veer-eh1` | [VeeR EH1](https://github.com/chipsalliance/Cores-VeeR-EH1) | RV32IMC_Zicsr_Zifencei_Zihpm | M only | `d04b1c7a`    |

EH1 has no A, no bit-manipulation, no U-mode and no PMP, so the configuration above is its maximum
feature set.

## Building and running

VeeR's testbench hardcodes the reset vector to 0 and ACT cannot link at address 0, so the tests are
linked at `TEST_BASE = 0x1000` and `run-veer.sh` prepends a two-instruction boot stub at 0.

```bash
# once: verilate the core
git clone https://github.com/chipsalliance/Cores-VeeR-EH1 ~/repos/Cores-VeeR-EH1
mkdir -p ~/repos/veer-builds/eh1 && cd ~/repos/veer-builds/eh1
RV_ROOT=~/repos/Cores-VeeR-EH1 make -f $RV_ROOT/tools/Makefile verilator-build

# build and run the tests
export PATH=$HOME/repos/veer-builds/bin:$PATH   # holds run-veer.sh
export VEER_SNAPSHOT=$HOME/repos/veer-builds/eh1
cd <act root>
make CONFIG_FILES=config/cores/veer-eh1/veer-eh1-rv32imc/test_config.yaml \
     EXCLUDE_EXTENSIONS=ExceptionsSm,Sm,ExceptionsZc --jobs $(nproc)
./run_tests.py "run-veer.sh --elf" work/veer-eh1-rv32imc/elfs
```

The three excluded suites fail during signature generation on the reference model, not on the DUT;
see the findings write-up for why.
