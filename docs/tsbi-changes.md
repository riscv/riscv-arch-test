# Changes to implement T-SBI

- Ensure extension works on all simulators and has 100% coverage, and measure instruction count and number of traps
- Review test plans. Determine if any coverpoints need to go into Sm suite because they run in machine mode (e.g. those that set medeleg=0)
  - Update coverpoints for Sm
  - Move tests for these coverpoints to a Sm suite
  - Update normative rules that moved
  - Confirm dynamic instruction count and number of traps doesn't change (or changes are explained)
- `from testgen.asm.tsbi import tsbi_call`
- Set `extra_defines=["#define BOOT_TO_SMODE"]` (or U-mode) until all modules are ported to T-SBI and the boot code is changed to boot to the right mode
- Remove RVTEST_GOTO_MMODE calls (or replace with RVTEST_TSBI_GOTO_MMODE in Sm suites where necessary)
- Replace RVTEST_GOTO_LOWER_MODE SMODE/UMODE with RVTEST_TSBI_GOTO_SMODE / RVTEST_TSBI_GOTO_UMODE
- Replace accesses to higher privilege CSRs with tsbi_call producing TSBI_CSR_READ etc.
  - `tsbi_call(f"csrr x{save_reg}, mstatus")`
  - search for and specially handle medeleg / mideleg CSR accesses, which probably indicate coverpoint should move to Sm suite
- change ecalls to RVTEST_TSBI_ECALL_TEST followed by write_sigupd(10, test_data) to check value returned in a0
- Confirm tests still run on all simulators and have 100% coverage
- Check whether dynamic instruction count and number of traps changed in unexpected ways. How much performance did this cost?
- Review whether tests changed in any significant way.

Notes for AGENTS:

- Boot mode is selected with `extra_defines=["#define BOOT_TO_SMODE"]` or `"#define BOOT_TO_MMODE"` on `@add_priv_test_generator`. The boot chain stops at the named mode. Otherwise, the test boots to the lowest supported mode (U if supported, otherwise M).
- Mode changes in converted suites use the assembler macros `RVTEST_TSBI_GOTO_MMODE` / `RVTEST_TSBI_GOTO_SMODE` / `RVTEST_TSBI_GOTO_UMODE`, never the legacy `RVTEST_GOTO_MMODE` / `RVTEST_GOTO_LOWER_MODE`. `TSBI_GOTO_*` (no `RVTEST_` prefix) are the a0 opcode constants; emitting one bare assembles as `0x2 # ...` and fails with "junk at end of line".
- Privileged CSR instructions from a lower mode go through `tsbi_call("csrw mstatus, x{reg}")` from `testgen.asm.tsbi`, which marshals rs1/rs2/rd through a1/a2/a0 and re-encodes the instruction. a0-a2 are reserved out of the priv register pool for this, and there is no need to exclude them when getting registers. The handler executes only instructions listed in `tsbi_instr_table` (`tests/env/rvtest_trap_handler.h`); a CSR missing from that table fails at run time with `T-SBI ERROR: requested instruction not found in tsbi_instr_table`. `medeleg` is deliberately not in the table.
- Coverpoints that need M-mode by construction (sweeps of `mstatus.TSR`, `cp_shadow`'s adjacent write-then-read, `*_from_m` accesses) belong in `Sm`, with the generated code under `#ifdef S_SUPPORTED` and the coverpoints under `` `ifdef S_SUPPORTED `` in `Sm_coverage.svh`. Moving a coverpoint between suites means moving its references in `coverpoints/norm/*.yaml` (normative rule -> coverpoint map, free text consumed by the CTP generators) as well.
