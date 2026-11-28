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

`install-shakti.sh` builds E-class from `base-sim/templates/rv32imac.inc` with the reset PC at the
base of RAM and 16 PMP entries, and without user-level traps, the instruction trace, debug
triggers or the event counter. Its comments give the reason for each option and for the patches to
the build flow.

## The testbench

base-sim has main memory at 0x8000_0000 (32 MB), loaded from `code.mem`, a CLINT at 0x0200_0000, a
UART at 0x1_1300, and an error slave behind every unmapped address. A write to 0x2_000C ends the
simulation. The testbench copies the UART's output to `app_log` and always exits 0, so
`run-shakti.sh` runs each test in its own directory and prints `app_log`; a test that never ends is
stopped by run_tests.py's timeout. The installer adds a byte register at 0x20004 to the
signature-dump device and connects it to the core's external interrupt input (MEIP).

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
example `BSC_PLATFORM=rockylinux-9.5`.

`ci.yaml` excludes the tests that fail on E-class bugs, with the cause of each.
