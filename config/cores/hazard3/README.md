# ACT Configuration for the Hazard3 Core

[Hazard3](https://github.com/Wren6991/Hazard3) is a 32-bit RISC-V core by Luke Wren, the CPU in the
Raspberry Pi RP2350. The configuration runs Hazard3's Verilator testbench, pinned to commit `ba0c83c`
on the `develop` branch.

| Config                    | ISA                                                                                     | Modes                 |
| ------------------------- | --------------------------------------------------------------------------------------- | --------------------- |
| `hazard3-rv32imacb-u-pmp` | RV32IMAC_Zba_Zbb_Zbc_Zbs_Zbkb_Zbkc_Zbkx_Zcb_Zicsr_Zifencei_Zicntr_Zihintntl_Zihintpause | M + U, 16 PMP regions |

Hazard3 implements privileged specification 1.12.

The install script builds the testbench from its default configuration, `config_default.vh`, with
the reset vector at the base of RAM, 16 PMP regions, zero `mvendorid` and `mconfigptr`, and the
unratified and custom extensions turned off. The script lists each change and its reason.

## Building and running

```bash
.github/scripts/install-hazard3.sh ~/repos/Hazard3-builds
export PATH=$HOME/repos/Hazard3-builds/bin:$PATH
export HAZARD3_SIM=$HOME/repos/Hazard3-builds/bin/hazard3-tb
make hazard3-rv32imacb-u-pmp
```

The install script builds Verilator and the testbench and installs the `run-hazard3.sh` runner.
The two exports do what `.github/scripts/setup-hazard3.sh` does in CI.
