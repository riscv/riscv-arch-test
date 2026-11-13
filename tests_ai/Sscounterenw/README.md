# Sscounterenw (and Shcounterenw)

## How it is tested

Generator: `gen/gen_Sscounterenw.py`, which also writes `Shcounterenw/` (same structure for hcounteren).
A counter is "not read-only zero" when a nonzero value written to its mhpmcounter reads back nonzero (with event
0 it does not count). The mask NZ of such counters is built first; then scounteren (hcounteren) is written with
all ones, 0, 0x55555550, 0xAAAAAAA8 and a random pattern, and single bits are set and cleared with csrs/csrc:
on NZ bits the read-back must equal what was written. mcounteren (and, for hcounteren, scounteren) must not
change. Bits of read-only-zero counters and CY/TM/IR are not constrained by the rule and are masked off.

- `<rule>.S` boots to S-mode and writes the mhpmcounters through T-SBI, which offers them only with Sscofpmf.
  Without Sscofpmf it can only count as present an hpmcounter that reads nonzero, so on such harts it usually
  checks nothing.
- `<rule>_Sm.S` boots to M-mode (requires Sm) and writes every mhpmcounter directly, so it decides for every
  counter.

## Rules not tested here

None: each extension has one rule (`Sscounterenw_hpmcounter_scounteren`, `Shcounterenw_hpmcounter_hcounteren`).

## Subtleties

- Spike hardwires mhpmcounter3..31 to 0 (riscv-software-src/riscv-isa-sim#2370), and Imperas without Sscofpmf
  leaves the mcounteren HPM bits read-only zero, so NZ is 0 there and the check is vacuous.
- The S-mode probe reads an hpmcounter only if its mcounteren bit reads back 1 (otherwise the read would trap).
