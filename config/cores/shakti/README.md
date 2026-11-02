# ACT Configurations for the Shakti E-class and C-class Cores

[Shakti](https://shakti.org.in) is IIT Madras's family of RISC-V cores, written in Bluespec
SystemVerilog. Both configurations compile the core with the open-source Bluespec compiler (bsc
2025.01.1) and simulate the core's own test SoC under Verilator 5.052.

| Config                   | Core                                                                                 | ISA                                                               | Modes                         |
| ------------------------ | ------------------------------------------------------------------------------------ | ----------------------------------------------------------------- | ----------------------------- |
| `shakti-eclass-rv32imac` | [E-class](https://gitlab.com/shaktiproject/cores/e-class) `e8a0dfd` (release 1.10.2) | RV32IMAC_Zicsr_Zifencei_Zicntr_Zihpm_Zihintntl_Zihintpause        | M + U, 16 PMP entries         |
| `shakti-cclass-rv64gc`   | [C-class](https://gitlab.com/shaktiproject/cores/c-class) `6feeb42`                  | RV64IMAFDC_Zicsr_Zifencei_Zicntr_Zihpm_Zihintntl_Zihintpause_Sv39 | M + S + U, 8 of 16 PMP usable |

E-class implements privileged specification 1.10 and C-class 1.11 with the 1.12 `menvcfg`;
both configurations declare `Sm` 1.11.

## Build options

`install-shakti.sh` builds each core from one of its own sample configurations and changes only
the options below. The script repeats each reason.

E-class, from `base-sim/templates/rv32imac.inc`:

- `USERTRAPS=disable`: no user-level interrupts (the withdrawn N extension), which neither UDB
  nor Sail models.
- `RESETPC=0x80000000`: start at the base of RAM, where the test is loaded, instead of in the
  boot ROM.
- `RTLDUMP=disable`: no instruction trace. The trace option also sets `misa.S` and clears
  `misa.N` to match Spike.
- `TRIGGERS=0`, `COUNTERS=0`: no debug triggers (Sdtrig is not claimed) and no event counter.
- `PMPSIZE=16` instead of 4: ACT needs at least 8 PMP entries.

C-class, from `sample_config/c64`:

- `reset_pc: 0x80000000`, for the same reason as E-class.
- 8 usable PMP entries instead of 4, and the CSRs of all 16 present. csrbox 1.12.0 generates
  BSV that does not compile for RV64 entries 8 to 15, so those are read-only zero, and the
  `pmpentries` define is set to 8 to match what csrbox builds.
- `medeleg` and `mideleg` masks that delegate only what the privileged specification allows.
  The sample's 0xF7FF also makes reserved and machine-interrupt bits writable.

The script also patches the build flows for current tools: E-class takes the three changes of
its upstream fix for [e-class#94](https://gitlab.com/shaktiproject/cores/e-class/-/issues/94)
(a smaller GHC stack limit, no `basicinout` Verilog filter, `--no-timing`), and both drop
`-static` from the Verilator link and silence Verilator 5.052's `MULTIDRIVEN` warning on bsc's
`FIFOL1.v`. bsc 2026.07.1 stops on E-class with an internal error, so bsc is pinned to
2025.01.1. C-class's Python configurator, `soc_config` 3.0.3, runs in a virtual environment.

## The testbenches

Both test SoCs have main memory at 0x8000_0000 (32 MB on E-class, 64 MB on C-class), loaded
from `code.mem`, a CLINT at 0x0200_0000, a UART at 0x1_1300, and an error slave behind every
unmapped address. A write to 0x2_000C ends the simulation. The testbench copies the UART's
output to `app_log` and always exits 0, so `run-shakti.sh` runs each test in its own directory
and passes it only if `app_log` holds `RVCP-SUMMARY: TEST PASSED`; a test that never ends is
stopped by the runner's timeout. On C-class, a byte load from the UART status register never
completes, so the console macros read it with `lhu`, and committing `j .` also ends the
simulation. Neither SoC connects an external interrupt source.

## Checked with the UDB feature extractor

Both configurations were checked against the UDB feature extractor (riscv-arch-test #2442) run on
these simulators. C-class's was seeded from it. Where they still differ, the configuration is
right and the extractor measured something else or assumed a value:

- E-class `MTVEC_ILLEGAL_WRITE_BEHAVIOR` is `custom`, not `retain`: a write with MODE 2 or 3
  keeps the old MODE but takes the new BASE.
- `MEI_INTR_IMPL` is false on both: `mie.MEIE` is writable, but neither SoC drives the external
  interrupt inputs.
- E-class `REPORT_VA_IN_MTVAL_ON_BREAKPOINT` is true: `ebreak` writes PC + 1 to mtval, which is
  neither the PC nor 0, and the tests report it.
- E-class `Zihintntl` and `Zihintpause` are listed; the extractor does not test them.
- C-class drops `Sscounterenw` (`scounteren` cannot enable `hpmcounter5` and `hpmcounter6`), and
  uses the `medeleg`, `mideleg` and `satp.ASID` values of the build above rather than those of
  the sample configuration, which the extractor measured.
- Values the extractor cannot measure or assumed (`PMA_GRANULARITY`,
  `PRECISE_SYNCHRONOUS_EXCEPTIONS`, `LRSC_MISALIGNED_BEHAVIOR`, the load and store access-fault
  mtval reports) come from the RTL or from the test results.

## Building and running

```bash
.github/scripts/install-shakti.sh $HOME/shakti
export PATH=$HOME/shakti/bin:$PATH
make shakti
```

`install-shakti.sh` builds Verilator, unpacks bsc, builds both simulators as
`shakti-eclass-sim` and `shakti-cclass-sim` in `bin/`, and installs `run-shakti.sh` beside them.
It uses the bsc tarball for Ubuntu 24.04; set `BSC_PLATFORM` (and `BSC_SHA256`) for another
platform, for example `BSC_PLATFORM=rockylinux-9.5`. The export matches what
`setup-shakti.sh` sets in CI.

Both configurations share `ci.yaml`, so its exclusions apply to both. Each entry says which core
it is for.
