# ACT Configuration for the BSC Sargantana Core

[Sargantana](https://github.com/bsc-loca/sargantana) is a 64-bit RISC-V core from the Barcelona
Supercomputing Center, tested as integrated in [core_tile](https://github.com/bsc-loca/core_tile)
(instruction cache, OpenHW HPDcache and MMU) under Verilator, pinned to core_tile `2528e7df`
(core `403975c`).

| Config                  | ISA                                            | Modes     |
| ----------------------- | ---------------------------------------------- | --------- |
| `sargantana-rv64imafdb` | RV64IMAFDB_Zicsr_Zifencei_Zicond_Zicbom_Zicboz | M + S + U |

- No C extension: `misa` bit 2 is hardwired to zero, IALIGN is 32 and `mepc` masks bit 1.
- No PMP: `pmpcfg0-3` and `pmpaddr0-15` read zero and ignore writes; `NUM_PMP_ENTRIES` is 0.
- No misaligned support: every misaligned load, store, AMO and LR/SC traps.
- Sv39 and Bare only, with Svade; no Svadu, Svnapot, Svpbmt or Svinval.
- `Sm 1.12` (`menvcfg` and `mstateen0-3` are implemented).
- No interrupt controller: the testbench ties the timer, software and external interrupt pins and
  the `time` input to zero; `RVMODEL_MTIME_ADDRESS` is undefined.
- `misa` reports V and H, but neither is claimed.

## RTL configuration

The shipped `drac_pkg::DracDefaultConfig`, unchanged.

## Building and running

```bash
git clone --recursive https://github.com/bsc-loca/core_tile ~/repos/core_tile
cd ~/repos/core_tile && make -j"$(nproc)" sim
export PATH=<act root>/.github/scripts:$PATH
export SARGANTANA_TILE=$HOME/repos/core_tile
cd <act root>
make CONFIG_FILES=config/cores/sargantana/sargantana-rv64imafdb/test_config.yaml
./run_tests.py "run-sargantana.sh --elf" work/sargantana-rv64imafdb/elfs
```

## Platform

- `tohost` must be 64-byte aligned: the tile matches the HPDcache write-buffer request address
  against the `tohost` symbol. `link.ld` places the HTIF block on 64-byte boundaries.
- `RVMODEL_IO_WRITE_STR` copies the string to a word-aligned staging buffer and delays briefly
  before writing `tohost`.
