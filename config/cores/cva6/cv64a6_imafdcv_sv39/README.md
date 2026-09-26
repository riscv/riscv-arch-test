# DUT configuration for CVA6 + Ara (`cv64a6_imafdcv_sv39`)

This is ACT's first vector-capable RTL DUT configuration.

| Item        | Value                                                                                             |
| ----------- | ------------------------------------------------------------------------------------------------- |
| Core        | CVA6 `cv64a6_imafdcv_sv39` with the Ara vector unit                                               |
| ISA         | RV64IMAFDCV, Sm 1.12, S, U, Sv39, Svade, Zihpm                                                    |
| VLEN / ELEN | 512 / 64                                                                                          |
| Lanes       | 4                                                                                                 |
| Simulator   | Verilator, **hierarchical** build                                                                 |
| Ara         | [`34bd3bc1`](https://github.com/pulp-platform/ara/tree/34bd3bc152421b4601a7bf3d6e8e91ffb545c99e)  |
| CVA6        | [`99eac9a6`](https://github.com/pulp-platform/cva6/tree/99eac9a649001bdf5b8f9da52e0ca73d5c48db1c) |

`cv64a6_imafdcv_sv39` is the only CVA6 configuration Ara attaches to (`hardware/Makefile:112`),
so the name is forced rather than chosen.

## Building and running

```
make CONFIG_FILES=config/cores/cva6/cv64a6_imafdcv_sv39/test_config.yaml
./run_tests.py "$(cat config/cores/cva6/cv64a6_imafdcv_sv39/run_cmd.txt)" \
    work/cv64a6_imafdcv_sv39/elfs
```

`run-ara.sh` expects a verilated model at `$ARA_SNAPSHOT/verilator/Vara_tb_verilator`
(default `~/repos/ara-builds/hier4v512`). `.github/scripts/install-ara.sh` builds one from
scratch; `setup-ara.sh` applies the one testbench patch that is required (see below).

## Things worth knowing before changing this config

- **The hierarchical Verilator build is not optional.** A flat build runs at roughly
  100 cycles/s against ~15,000 cycles/s hierarchical. `--hierarchical` needs Verilator
  5.046 or newer; Ara pins 5.047-devel as a submodule and `make verilator` builds it in
  about four minutes. Verilator 5.036 drops the `+incdir+`/`+define+` lines from Bender's
  flist and the design will not elaborate.

- **VLEN 512, not Ara's default 4096.** `vlen` is an independent `-G` parameter. 4096 is
  about 15x more wall clock and 8x more signature memory for no extra architectural
  coverage.

- **Termination is not HTIF.** A 64-bit store to `0xD000_0000` ends the simulation and the
  testbench exits with `(value >> 1)`. The `tohost`-based macros in
  `config/cores/cva6/rvmodel_macros.h` (used by cv32a65x) will simply hang this DUT.

- **A cycle-limit timeout exits 0.** `run-ara.sh` greps stdout for
  `Simulation timeout of` and converts it to a failure. Do not remove that check; 36 tests
  in this configuration hang, and without it they would all be scored as passes.

- **The testbench ELF loader window must be widened.** `hardware/tb/verilator/ara_tb.cpp`
  registers the L2 as 1 MiB and asserts that every ELF segment fits; ACT's vector ELFs
  exceed that. `setup-ara.sh` applies a documented one-line `sed` to `0x0100_0000`
  (the true L2 size) rather than carrying a fork.

- **`RAM_LENGTH` is 16 MiB, not the 1 GiB the decoder claims.** The physical L2 is
  `(2**22)/NrLanes` words of `32*NrLanes` bits = 2^24 bytes, and it is indexed with the low
  address bits, so anything above 16 MiB aliases instead of faulting.

- **Check `mtvec` before copying this config anywhere else.** CVA6 supports both direct and
  vectored mode, but forces `mtvec[7:1]` to zero in vectored mode, i.e. a 256-byte base
  alignment. Getting this wrong makes the reference model choose a different trap vector
  than the DUT and every test dies in the trap handler.

## Results

2361 tests selected, **347 pass**. The failures are dominated by a single DUT bug:
`vfirst.m` and `vcpop.m` ignore `vl`, and ACT's vector self-check macro is built out of
`vmsne.vv` + `vfirst.m`, so nearly every vector test fails on the check itself rather than
on the instruction under test. `ci.yaml` records a measured reason for every excluded
suite, and the full analysis — with RTL citations and directed-probe evidence for each
claim — is in the accompanying discrepancy report.

Suites that pass completely: `I` 51/51, `M` 13/13, `Zca` 32/32, `Zcd` 4/4, `Zicsr` 6/6,
`Zmmul` 5/5, `Zifencei` 1/1, `Zihpm` 2/2, `SmV` 6/6, `Svade` 2/2, `Svbare` 3/3,
`Sscounterenw` 1/1, `UF` 1/1. Also `Sv` 31/33, `D` 99/116, `F` 69/84, `Sm` 17/27.
