# ACT Configuration for CVA6 + Ara (`cv64a6_imafdcv_sv39`)

CVA6 `cv64a6_imafdcv_sv39` with the Ara vector unit, run under a hierarchical Verilator build.

| Item        | Value                                                                                             |
| ----------- | ------------------------------------------------------------------------------------------------- |
| ISA         | RV64IMAFDCV, Sm 1.12, S, U, Sv39, Svade, Zihpm                                                    |
| Modes       | M + S + U                                                                                         |
| VLEN / ELEN | 512 / 64                                                                                          |
| Lanes       | 4                                                                                                 |
| Ara         | [`34bd3bc1`](https://github.com/pulp-platform/ara/tree/34bd3bc152421b4601a7bf3d6e8e91ffb545c99e)  |
| CVA6        | [`99eac9a6`](https://github.com/pulp-platform/cva6/tree/99eac9a649001bdf5b8f9da52e0ca73d5c48db1c) |

- `cv64a6_imafdcv_sv39` is the only CVA6 configuration Ara attaches to.
- A, Zaamo and Zalrsc are not claimed.
- Misaligned loads and stores are not supported (`MISALIGNED_LDST: false`).
- `mtvec` supports direct and vectored mode; vectored mode forces `mtvec[7:1]` to zero.

## RTL configuration

- `vlen=512` (Ara's default is 4096), `nr_lanes=4`.
- Verilator `--hierarchical` build; needs Verilator 5.046 or newer (Ara pins 5.047-devel).
- `setup-ara.sh` widens the L2 ELF loader window in `hardware/tb/verilator/ara_tb.cpp` from
  1 MiB to `0x0100_0000`.

## Building and running

`run-ara.sh` expects a verilated model at `$ARA_SNAPSHOT/verilator/Vara_tb_verilator` (default
`~/repos/ara-builds/hier4v512`); `.github/scripts/install-ara.sh` builds one.

```bash
make CONFIG_FILES=config/cores/cva6/cv64a6_imafdcv_sv39/test_config.yaml
./run_tests.py "$(cat config/cores/cva6/cv64a6_imafdcv_sv39/run_cmd.txt)" \
    work/cv64a6_imafdcv_sv39/elfs
```

## Platform

- RAM: 16 MiB L2 (`RAM_LENGTH`); addresses above 16 MiB alias.
- Exit: a 64-bit store to `0xD000_0000` ends the simulation with exit code `value >> 1`. The
  `tohost`-based macros in `config/cores/cva6/rvmodel_macros.h` do not apply.
- A cycle-limit timeout exits 0; `run-ara.sh` reports `Simulation timeout of` as a failure.
