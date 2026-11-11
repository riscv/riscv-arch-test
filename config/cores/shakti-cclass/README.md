# ACT Configuration for the Shakti C-class Core

[Shakti](https://shakti.org.in) is IIT Madras's family of RISC-V cores, written in Bluespec
SystemVerilog. This configuration compiles C-class with the open-source Bluespec compiler (bsc
2025.01.1) and simulates the core's own test SoC under Verilator 5.052. The E-class
configuration is in [`../shakti-eclass`](../shakti-eclass); the two share their install and run
scripts.

| Config                 | Core                                                                                | ISA                                                               | Modes                         |
| ---------------------- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------- | ----------------------------- |
| `shakti-cclass-rv64gc` | [C-class](https://gitlab.com/shaktiproject/cores/c-class) `f527753` (release 6.1.0) | RV64IMAFDC_Zicsr_Zifencei_Zicntr_Zihpm_Zihintntl_Zihintpause_Sv39 | M + S + U, 8 of 16 PMP usable |

C-class implements privileged specification 1.11 with the 1.12 `menvcfg`; the configuration
declares `Sm` 1.11.

## Build options

`install-shakti.sh` builds C-class from `sample_config/c64` and changes only the options below.
The script repeats each reason.

- `reset_pc: 0x80000000`: start at the base of RAM, where the test is loaded, instead of in the
  boot ROM.
- 8 usable PMP entries instead of 4, and the CSRs of all 16 present. csrbox 1.12.0 generates
  BSV that does not compile for RV64 entries 8 to 15, so those are read-only zero, and the
  `pmpentries` define is set to 8 to match what csrbox builds.
- `medeleg` and `mideleg` masks that delegate only what the privileged specification allows.
  The sample's 0xF7FF also makes reserved and machine-interrupt bits writable.
- `satp.ASID` with 8 writable bits. The sample leaves the field unchanged on a write of all ones,
  the privileged specification's way to find ASIDLEN.

The script also drops `-static` from the Verilator link and silences Verilator 5.052's
`MULTIDRIVEN` warning on bsc's `FIFOL1.v`. bsc is pinned to 2025.01.1, as for E-class. C-class's
Python configurator, `soc_config` 3.0.4, runs in a virtual environment.

## The testbench

test_soc has main memory at 0x8000_0000 (64 MB), loaded from `code.mem`, a CLINT at
0x0200_0000, a UART at 0x1_1300, and an error slave behind every unmapped address. A write to
0x2_000C ends the simulation, and so does committing `j .`. The testbench copies the UART's
output to `app_log` and always exits 0, so `run-shakti.sh` runs each test in its own directory
and passes it only if `app_log` holds `RVCP-SUMMARY: TEST PASSED`; a test that never ends is
stopped by the runner's timeout. A byte load from the UART status register never completes, so
the console macros read it with `lhu`. The installer adds byte registers at 0x20004 (MEIP) and
0x20005 (SEIP) to the signature-dump device and connects them to the core's interrupt inputs;
the interrupt macros set and clear each input independently.

## Checked with the UDB feature extractor

The configuration was seeded from the UDB feature extractor (riscv-arch-test #2442) run on this
simulator. Where they still differ, the configuration is right and the extractor measured
something else or assumed a value:

- `MEI_INTR_IMPL` is true because `mie.MEIE` is writable. The ACT testbench supplies an external
  interrupt source through the registers described above.
- `Sscounterenw` is dropped (`scounteren` cannot enable `hpmcounter5` and `hpmcounter6`), and the
  `medeleg`, `mideleg` and `satp.ASID` values are those of the build above rather than those of
  the sample configuration, which the extractor measured.
- `Zihintntl` and `Zihintpause` are listed; the extractor does not test them.
- Values the extractor cannot measure or assumed (`PMA_GRANULARITY`,
  `PRECISE_SYNCHRONOUS_EXCEPTIONS`, `LRSC_MISALIGNED_BEHAVIOR`) come from the RTL or from the
  test results.

## Building and running

```bash
.github/scripts/install-shakti.sh $HOME/shakti cclass
export PATH=$HOME/shakti/bin:$PATH
make shakti-cclass
```

`install-shakti.sh` builds Verilator, unpacks bsc, builds the simulator as `shakti-cclass-sim`
in `bin/`, and installs `run-shakti.sh` beside it. Without the core argument it takes the core
from the install directory's name (`shakti-cclass`), which is how CI calls it. It uses the bsc
tarball for Ubuntu 24.04; set `BSC_PLATFORM` (and `BSC_SHA256`) for another platform, for
example `BSC_PLATFORM=rockylinux-9.5`. The export matches what `setup-shakti.sh` sets in CI.

`ci.yaml` excludes the tests that fail on C-class bugs, with the cause of each and its upstream
issue where one is filed.
