# ACT Configuration for the OpenHW CVA6 Verilator Testharness

These configurations run the [CVA6](https://github.com/openhwfoundation/cva6) core in its Verilator
testharness (`corev_apu/tb/ariane_testharness.sv`), pinned to CVA6 commit `81245a4`.

| Config     | ISA                                              | Modes | PMP                                  |
| ---------- | ------------------------------------------------ | ----- | ------------------------------------ |
| `cv32a65x` | RV32IMCB_Zicsr_Zifencei_Zcb_Zba_Zbb_Zbc_Zbkc_Zbs | M     | 8 TOR-only entries, not declared yet |
| `cv32a60x` | RV32IMCB_Zicsr_Zifencei_Zcb_Zba_Zbb_Zbc_Zbkc_Zbs | M     | none                                 |

`cv32a65x` is the 6-stage, M-mode-only release configuration described in the
[CV32A65X Design Document](https://docs.openhwfoundation.org/projects/cva6-user-manual/04_cv32a65x/design/design.html).
Its RTL parameters are in `core/include/cv32a65x_config_pkg.sv`. `cv32a60x` has the same ISA and
differs in microarchitecture: it is single-issue (`SuperscalarEn=0`), has no ALU bypass
(`ALUBypass=0`), has 4 scoreboard entries instead of 8, and has no PMP (`NrPMPEntries=0`). Its
parameters are in `core/include/cv32a60x_config_pkg.sv`. Both share `ci.yaml` and
`install-cva6.sh`.

Both cores set `misa.B` (`RVB=1`), and B is Zba + Zbb + Zbs, so the ISA string includes B.
`cv32a65x` has 8 TOR-only PMP entries in RTL. The configs declare none until ACT supports
PMP without NAPOT (riscv-arch-test#2904).

## Building and running

```bash
.github/scripts/install-cva6.sh ~/repos/cva6-builds
export PATH=$HOME/repos/cva6-builds/bin:$PATH
export CVA6_SNAPSHOT=$HOME/repos/cva6-builds
make cv32a65x EXCLUDE_EXTENSIONS=PMP_Sm_cfg_A_tor_zero
make cv32a60x
```

The install script clones CVA6, builds the Verilator and Spike versions CVA6's own CI uses (the
testharness links Spike's libraries), verilates one testharness per configuration under
`<install-dir>/cva6/work-ver-<config>/`, and installs the shared `run-cva6.sh` runner. It needs
`riscv64-unknown-elf-gcc` on `PATH`. The two exports do what `.github/scripts/setup-cva6.sh` does
in CI. The excluded extensions and their reasons are listed in `ci.yaml`. The
`PMP_Sm_cfg_A_tor_zero` exclusion is preemptive: no PMP test runs until `cv32a65x` declares
its PMP entries.

The testharness has no external interrupt source, so `install-cva6.sh` patches it to replace
the GPIO error slave at `0x4000_0000` with an interrupt generator that matches Sail's
`simple_interrupt_generator`. Writing `0x80000800` to `0x4000_0004` raises the machine external
interrupt, and writing `0x00000800` clears it. `sail.json` places Sail's generator at the same
address, so `RVMODEL_SET_MEXT_INT` and `RVMODEL_CLR_MEXT_INT` drive both models with one store.

The testharness halts on a write to `tohost`: 1 is a pass, any other value a fail. The runner
passes the `tohost` address to the simulator and turns the testharness verdict into an `RVCP-SUMMARY`
line. Each simulation uses about 2.5 GB of memory and `make` runs one per CPU, so on machines with
less than 2.5 GB per CPU run the ELFs with fewer jobs (`./run_tests.py -j N`). For example:

```bash
./run_tests.py -j 4 "$(cat config/cores/cva6/cv32a65x/run_cmd.txt)" work/cv32a65x/elfs
```

With `DEBUG=True`, the runner also writes `work/<config>/logs/<test>.trace.log` (RVFI trace
decoded with `spike-dasm`) and `<test>.fst` (waveform).
