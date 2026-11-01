# ACT Configuration for the OpenHW CVA6 Verilator Testharness

These configurations run the [CVA6](https://github.com/openhwfoundation/cva6) core in its Verilator
testharness (`corev_apu/tb/ariane_testharness.sv`), pinned to CVA6 commit `81245a4`.

| Config               | ISA                                                                                                    | Modes   | PMP                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------ | ------- | ------------------------------------ |
| `cv32a65x`           | RV32IMCB_Zicsr_Zifencei_Zcb_Zba_Zbb_Zbc_Zbkc_Zbs                                                       | M       | 8 TOR-only entries, not declared yet |
| `cv32a60x`           | RV32IMCB_Zicsr_Zifencei_Zcb_Zba_Zbb_Zbc_Zbkc_Zbs                                                       | M       | none                                 |
| `cv64a6_imafdc_sv39` | RV64IMAFDC_Zicsr_Zifencei_Zicntr_Zihpm_Zicbom_Zicond_Zcb_Zba_Zbb_Zbc_Zbs_Zbkb_Zbkc_Zbkx_Zkne_Zknd_Zknh | M, S, U | 8 entries, NAPOT and TOR             |

`cv32a65x` is the 6-stage, M-mode-only release configuration described in the
[CV32A65X Design Document](https://docs.openhwfoundation.org/projects/cva6-user-manual/04_cv32a65x/design/design.html).
Its RTL parameters are in `core/include/cv32a65x_config_pkg.sv`. `cv32a60x` has the same ISA and
differs in microarchitecture: it is single-issue (`SuperscalarEn=0`), has no ALU bypass
(`ALUBypass=0`), has 4 scoreboard entries instead of 8, and has no PMP (`NrPMPEntries=0`). Its
parameters are in `core/include/cv32a60x_config_pkg.sv`.

`cv64a6_imafdc_sv39` is the 64-bit application-class configuration with S and U modes, Sv39,
8 PMP entries and the HPDcache. It runs the `cv64a6_imafdc_sv39_hpdcache` target, whose
parameters are in `core/include/cv64a6_imafdc_sv39_hpdcache_config_pkg.sv`. All three configs
share `ci.yaml` and `install-cva6.sh`.

`cv32a65x` has 8 TOR-only PMP entries in RTL. The configs declare none until ACT supports
PMP without NAPOT (riscv-arch-test#2904).

## Building and running

```bash
.github/scripts/install-cva6.sh ~/repos/cva6-builds
export PATH=$HOME/repos/cva6-builds/bin:$PATH
export CVA6_SNAPSHOT=$HOME/repos/cva6-builds
make cv32a65x EXCLUDE_EXTENSIONS=PMP_Sm_cfg_A_tor_zero
make cv32a60x
make cv64a6_imafdc_sv39 EXCLUDE_EXTENSIONS="$(.github/scripts/ci_config.py --exclusions config/cores/cva6/ci.yaml)"
```

The install script clones CVA6, builds the Verilator and Spike versions CVA6's own CI uses (the
testharness links Spike's libraries), verilates one testharness per configuration under
`<install-dir>/cva6/work-ver-<config>/`, and installs the shared `run-cva6.sh` runner. It needs
`riscv64-unknown-elf-gcc` on `PATH`. The two exports do what `.github/scripts/setup-cva6.sh` does
in CI. The excluded extensions and their reasons are listed in `ci.yaml`. The
`PMP_Sm_cfg_A_tor_zero` exclusion is preemptive: no PMP test runs until `cv32a65x` declares
its PMP entries.

The Verilator testharness has no external interrupt source: the GPIO slot is an error slave and
the PLIC's UART, SPI and Ethernet sources are disabled. The configs therefore set
`MEI_INTR_IMPL: false`, and the machine external interrupt test cases are skipped.

The testharness halts on a write to `tohost`: 1 is a pass, any other value a fail. The runner
passes the `tohost` address to the simulator and turns the testharness verdict into an `RVCP-SUMMARY`
line. Each simulation uses about 2.5 GB of memory and `make` runs one per CPU, so on machines with
less than 2.5 GB per CPU run the ELFs with fewer jobs (`./run_tests.py -j N`). For example:

```bash
./run_tests.py -j 4 "$(cat config/cores/cva6/cv32a65x/run_cmd.txt)" work/cv32a65x/elfs
```

With `DEBUG=True`, the runner also writes `work/<config>/logs/<test>.trace.log` (RVFI trace
decoded with `spike-dasm`) and `<test>.fst` (waveform).
