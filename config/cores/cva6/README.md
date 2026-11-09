# ACT Configuration for the OpenHW CVA6 Verilator Testharness

These configurations run the [CVA6](https://github.com/openhwfoundation/cva6) core in its Verilator
testharness (`corev_apu/tb/ariane_testharness.sv`), pinned to CVA6 commit `e9b8e8e` on
`master_candidate`, the development branch. `master` is read-only and kept for legacy integrations.

| Config              | ISA                                                 | Modes   | PMP                                  |
| ------------------- | --------------------------------------------------- | ------- | ------------------------------------ |
| `cv32a65x`          | RV32IMCB_Zicsr_Zifencei_Zcb_Zba_Zbb_Zbc_Zbkc_Zbs    | M       | 8 TOR-only entries, not declared yet |
| `cv32a60x`          | RV32IMCB_Zicsr_Zifencei_Zcb_Zba_Zbb_Zbc_Zbkc_Zbs    | M       | none                                 |
| `fpga_linux_cv32a6` | RV32IMACB_Zicsr_Zifencei_Zicbom_Zba_Zbb_Zbc_Zbs_Zkn | M, S, U | 8 entries                            |

Each config is named after a CVA6 target, whose parameters are in
`config/target/<target>/rtl_cfg_pkg.sv`. `cv32a65x` is the superscalar, M-mode-only release
configuration described in the
[CV32A65X Design Document](https://docs.openhwfoundation.org/projects/cva6-user-manual/04_cv32a65x/design/design.html).
`cv32a60x` has the same ISA and differs in microarchitecture: it is single-issue
(`SuperscalarEn=0`), has 4 scoreboard entries instead of 8, and has no PMP (`NrPMPEntries=0`). Both
use the OBI memory subsystem, which has no caches.

`fpga_linux_cv32a6` is the 32-bit Linux configuration: single-issue, with S and U modes, Sv32,
8 PMP entries, Zicbom and machine software interrupts. All three configurations share `ci.yaml` and
`install-cva6.sh`.

`cv32a65x` has 8 TOR-only PMP entries in RTL. Its config declares none until ACT supports
PMP without NAPOT (riscv-arch-test#2904).

CI runs only `fpga_linux_cv32a6`. `cv32a65x` and `cv32a60x` are OBI targets, and CVA6's Verilator
testharness supports only AXI targets, so `ci.yaml` lists them in `exclude_configs` and the install
script does not build them. Their configs are kept for when CVA6 has an OBI Verilator testbench.

## Building and running

```bash
.github/scripts/install-cva6.sh ~/repos/cva6-builds
export PATH=$HOME/repos/cva6-builds/bin:$PATH
export CVA6_SNAPSHOT=$HOME/repos/cva6-builds
EXCL="$(.github/scripts/ci_config.py --exclusions config/cores/cva6/ci.yaml)"
make fpga_linux_cv32a6 EXCLUDE_EXTENSIONS="$EXCL"
```

The install script clones CVA6, applies the submodule patches listed in CVA6's
`flows/config/dependencies.yml`, builds the Verilator and Spike versions CVA6's own CI uses (the
testharness links Spike's libraries), verilates one testharness per configuration under
`<install-dir>/cva6/work-ver-<config>/`, and installs the shared `run-cva6.sh` runner. It needs
`riscv64-unknown-elf-gcc` on `PATH`. The two exports do what `.github/scripts/setup-cva6.sh` does
in CI. The excluded extensions and their reasons are listed in `ci.yaml`.

The Verilator testharness has no external interrupt source: the GPIO slot is an error slave and
the PLIC's UART, SPI and Ethernet sources are disabled. The configs therefore set
`MEI_INTR_IMPL: false`, and the machine external interrupt test cases are skipped.

The testharness halts on a write to `tohost`: 1 is a pass, any other value a fail. The runner
passes the `tohost` address to the simulator and turns the testharness verdict into an `RVCP-SUMMARY`
line. Each simulation uses about 2.5 GB of memory and `make` runs one per CPU, so on machines with
less than 2.5 GB per CPU run the ELFs with fewer jobs (`./run_tests.py -j N`). For example:

```bash
./run_tests.py -j 4 "$(cat config/cores/cva6/fpga_linux_cv32a6/run_cmd.txt)" work/fpga_linux_cv32a6/elfs
```

With `DEBUG=True`, the runner also writes `work/<config>/logs/<test>.trace.log` (RVFI trace
decoded with `spike-dasm`) and `<test>.fst` (waveform).
