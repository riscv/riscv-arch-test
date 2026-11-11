# ACT Configuration for the Shakti E-class Core

[Shakti](https://shakti.org.in) is IIT Madras's family of RISC-V cores, written in Bluespec
SystemVerilog. This configuration compiles E-class with the open-source Bluespec compiler (bsc
2025.01.1) and simulates the core's own test SoC under Verilator 5.052. The C-class
configuration is in [`../shakti-cclass`](../shakti-cclass); the two share their install and run
scripts.

| Config                   | Core                                                                                 | ISA                                                        | Modes                 |
| ------------------------ | ------------------------------------------------------------------------------------ | ---------------------------------------------------------- | --------------------- |
| `shakti-eclass-rv32imac` | [E-class](https://gitlab.com/shaktiproject/cores/e-class) `e8a0dfd` (release 1.10.2) | RV32IMAC_Zicsr_Zifencei_Zicntr_Zihpm_Zihintntl_Zihintpause | M + U, 16 PMP entries |

E-class implements privileged specification 1.10; the configuration declares `Sm` 1.11.

## Build options

`install-shakti.sh` builds E-class from `base-sim/templates/rv32imac.inc` and changes only the
options below. The script repeats each reason.

- `USERTRAPS=disable`: no user-level interrupts (the withdrawn N extension), which neither UDB
  nor Sail models.
- `RESETPC=0x80000000`: start at the base of RAM, where the test is loaded, instead of in the
  boot ROM.
- `RTLDUMP=disable`: no instruction trace. The trace option also sets `misa.S` and clears
  `misa.N` to match Spike.
- `TRIGGERS=0`, `COUNTERS=0`: no debug triggers (Sdtrig is not claimed) and no event counter.
- `PMPSIZE=16` instead of 4: ACT needs at least 8 PMP entries.

The script also patches the build flow for current tools: it takes the three changes of the
upstream fix for [e-class#94](https://gitlab.com/shaktiproject/cores/e-class/-/issues/94) (a
smaller GHC stack limit, no `basicinout` Verilog filter, `--no-timing`), drops `-static` from the
Verilator link and silences Verilator 5.052's `MULTIDRIVEN` warning on bsc's `FIFOL1.v`. bsc
2026.07.1 stops on E-class with an internal error, so bsc is pinned to 2025.01.1.

## The testbench

base-sim has main memory at 0x8000_0000 (32 MB), loaded from `code.mem`, a CLINT at
0x0200_0000, a UART at 0x1_1300, and an error slave behind every unmapped address. A write to
0x2_000C ends the simulation. The testbench copies the UART's output to `app_log` and always
exits 0, so `run-shakti.sh` runs each test in its own directory and passes it only if `app_log`
holds `RVCP-SUMMARY: TEST PASSED`; a test that never ends is stopped by the runner's timeout. The
installer adds a byte register at 0x20004 to the signature-dump device and connects it to the
core's external interrupt input (MEIP).

## Checked with the UDB feature extractor

The configuration was checked against the UDB feature extractor (riscv-arch-test #2442) run on
this simulator. Where they still differ, the configuration is right and the extractor measured
something else or assumed a value:

- `MTVEC_ILLEGAL_WRITE_BEHAVIOR` is `custom`, not `retain`: a write with MODE 2 or 3 keeps the
  old MODE but takes the new BASE.
- `MEI_INTR_IMPL` is true because `mie.MEIE` is writable. The ACT testbench supplies an external
  interrupt source through the register described above.
- `REPORT_VA_IN_MTVAL_ON_BREAKPOINT` is true: `ebreak` writes PC + 1 to mtval, which is neither
  the PC nor 0, and the tests report it.
- `Zihintntl` and `Zihintpause` are listed; the extractor does not test them.
- Values the extractor cannot measure or assumed (`PMA_GRANULARITY`,
  `PRECISE_SYNCHRONOUS_EXCEPTIONS`, `LRSC_MISALIGNED_BEHAVIOR`, the load and store access-fault
  mtval reports) come from the RTL or from the test results.

## Building and running

```bash
.github/scripts/install-shakti.sh $HOME/shakti eclass
export PATH=$HOME/shakti/bin:$PATH
make shakti-eclass
```

`install-shakti.sh` builds Verilator, unpacks bsc, builds the simulator as `shakti-eclass-sim`
in `bin/`, and installs `run-shakti.sh` beside it. Without the core argument it takes the core
from the install directory's name (`shakti-eclass`), which is how CI calls it. It uses the bsc
tarball for Ubuntu 24.04; set `BSC_PLATFORM` (and `BSC_SHA256`) for another platform, for
example `BSC_PLATFORM=rockylinux-9.5`. The export matches what `setup-shakti.sh` sets in CI.

`ci.yaml` excludes the tests that fail on E-class bugs, with the cause of each.
