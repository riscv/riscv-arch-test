# ACT Configuration for the BSC Sargantana Core

[Sargantana](https://github.com/bsc-loca/sargantana) is a 64-bit RISC-V core from the Barcelona
Supercomputing Center. It is tested as integrated in [core_tile](https://github.com/bsc-loca/core_tile)
(Vidriol instruction cache, OpenHW HPDcache and MMU) under Verilator, pinned to core_tile `1b9529b5`
(v4.0.0; core `8db4398b`, v4.0) with the default `drac_pkg::DracDefaultConfig`.

| Config                 | ISA                                                                                                                          | Modes         |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ------------- |
| `sargantana4-rv64gcbh` | RV64IMAFDCBH_Zicsr_Zifencei_Zicond_Zicbom_Zicbop_Zicboz_Zicclsm_Zimop_Zawrs_Zfa_Zfhmin_Zcb_Zcmop_Sv39_Svpbmt_Svnapot_Svinval | M + S + U + H |

The vector unit (misa.V = 1) supports only LMUL <= 1, so neither V nor any Zve\* extension is claimed.

## Building and running

```bash
.github/scripts/install-sargantana.sh $HOME/sargantana
export PATH=$HOME/sargantana/bin:$PATH
export SARGANTANA_TILE=$HOME/sargantana/core_tile
make CONFIG_FILES=config/cores/sargantana/sargantana4-rv64gcbh/test_config.yaml
```

`install-sargantana.sh` builds Verilator and the core_tile simulator at the pinned commits and
installs `run-sargantana.sh`. The two exports match what `setup-sargantana.sh` sets in CI.
