# Changes to implement T-SBI

- Ensure extension works on all simulators and has 100% coverage, and measure instruction count and number of traps in table (along with max size of trap signature)
- Review test plans. Determine if any coverpoints need to go into a Sm suite because they run in machine mode (e.g. those that set medeleg=0)
  - Update coverpoints for Sm
  - Move tests for these coverpoints to a Sm suite
  - Update normative rules that moved
  - Confirm dynamic instruction count and number of traps doesn't change (or changes are explained)
- from testgen.asm.tsbi import tsbi_call
- Set extra_defines=["#define BOOT_TO_SMODE"] (or U-mode) until all modules are ported to T-SBI and the boot code is changed to boot to the right mode
- Remove RVTEST_GOTO_MMODE, RVTEST_GOTO_LOWER_MODE SMODE/UMODE calls in tests
- Replace RVTEST_GOTO_LOWER_MODE SMODE/UMODE with RVTEST_TSBI_GOTO_SMODE / RVTEST_TSBI_GOTO_UMODE
- Replace accesses to higher privilege with tsbi_call producing TSBI_CSR_READ etc.
  - tsbi_call(f"csrr x{save_reg}, mstatus")
  - search for and specially handle medeleg / mideleg CSR accesses, which probably shouldn't be in lower priv mode code
- change ecalls to RVTEST_TSBI_ECALL_TEST followed by write_sigupd(10, test_data) to check value returned in a0
- Confirm tests still run on all simulators and have 100% coverage
- Check whether dynamic instruction count and number of traps changed in unexpected ways. How much performance did this cost?
- Review whether tests changed in any significant way.
