# ACT Configuration for the BSC Sargantana Core

[Sargantana](https://github.com/bsc-loca/sargantana) is a 64-bit RISC-V core from the Barcelona
Supercomputing Center. It is tested as integrated in [core_tile](https://github.com/bsc-loca/core_tile)
(instruction cache, OpenHW HPDcache and MMU) under Verilator, pinned to core_tile `2528e7df`
(core `403975c`) with the default `drac_pkg::DracDefaultConfig`.

| Config                  | ISA                                                                    | Modes         |
| ----------------------- | ---------------------------------------------------------------------- | ------------- |
| `sargantana-rv64imafdb` | RV64IMAFDBH_Zicsr_Zifencei_Zicond_Zicbom_Zicbop_Zicboz_Zfa_Zfhmin_Sv39 | M + S + U + H |

## Building and running

```bash
.github/scripts/install-sargantana.sh $HOME/sargantana
export PATH=$HOME/sargantana/bin:$PATH
export SARGANTANA_TILE=$HOME/sargantana/core_tile
make sargantana-rv64imafdb
```

`install-sargantana.sh` builds Verilator and the core_tile simulator at the pinned commits and
installs `run-sargantana.sh`. The two exports match what `setup-sargantana.sh` sets in CI.
