# review_checks.py output

Read this when interpreting the output of `scripts/review_checks.py`.

The script reports:

- **Sources:**
  - a missing generator or testplan
  - stale generated tests
  - tests that reference a covergroup no coverpoint file defines
- **Suite type:**
  - a boot define that doesn't match the suite name
  - `RVTEST_TSBI_GOTO_MMODE` in a suite that boots to S or U
  - T-SBI calls in an unprivileged suite
  - legacy `RVTEST_GOTO_*` macros
- **Coverpoint text:** commented-out bins or coverpoints, and `ignore_bins` without a reason comment.
- **Guard names:** every `#ifdef`, `` `ifdef `` and `defined()` name that no config, header, or UDB parameter defines. These are likely typos.
- **UDB parameters:**
  - parameters defined by the suite's extension that the suite neither uses (`UDB_*`) nor maps in `coverpoints/param/<Suite>.yaml`
  - parameters it uses without mapping them
  - The script takes the parameter list from the pinned `udb` gem. To check against a riscv-unified-db checkout instead, pass `--udb-param-dir <udb>/spec/std/isa/param`. The canonical list is <https://github.com/riscv/riscv-unified-db/tree/main/spec/std/isa/param>; each YAML's `definedBy` names the extensions a parameter belongs to.
- **Normative-rule mapping:** entries in `coverpoints/norm/<Suite>.yaml` that point to coverpoints that don't exist, and the number of rules with no coverpoint.
- **Coverage:** covergroups below 100%.
- **Traps:**
  - any trap in an unprivileged suite
  - each config whose trap sequence (mode, cause, and testcase label) differs from `sail-rv32-max` or `sail-rv64-max`, with the first divergence
- **Size, instructions and traps per config:** for every test on every config, the ELF's loadable bytes, the dynamic instruction count and the number of traps taken, both on the DUT (from its `DEBUG=True` trace) and on the reference model under that config (from the `.sig.trace`).
  - Counting stops at `rvmodel_halt_pass`/`rvmodel_halt_fail`, so a simulator's halt latency is excluded. Spike, for example, spins about 4,000 instructions in `write_tohost_pass` before it notices `tohost`.
  - Traps are counted at the `trap_[MSV]handler` entry points. They include the framework's own ecalls (boot, T-SBI, mode changes), so even unprivileged suites show a few.
  - It reports each config's usual overhead once, then any test that departs from its config's usual overhead, each config's DUT/reference trap counts, and any test over 100,000 dynamic instructions, which should be split into more files.
  - `--metrics-csv FILE` writes the per-test table for deeper digging.
