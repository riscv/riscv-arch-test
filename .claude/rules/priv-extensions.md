---
paths:
  - "generators/testgen/src/testgen/priv/extensions/**/*.py"
---

These are privileged test generators, auto-discovered by the registry.

Key conventions:
- Use `@add_priv_test_generator("SuiteName", required_extensions=[...], ...)` decorator
- Function signature: `(test_data: TestData) -> list[str]` returning assembly lines
- Use `test_data.add_testcase(bin_name, coverpoint, covergroup)` to register testcases
- Use `test_data.int_regs.get_registers(n)` for register allocation, `return_registers()` when done
- CSR helpers: `csr_access_test()`, `csr_walk_test()`, `gen_csr_read_sigupd()`, `gen_csr_write_sigupd()` from `testgen.asm.csr`
- WARL fields with reserved values legalize implementation-defined (Sail may retain the old value, Spike may zero): never exact-compare a readback after writing a reserved value. Pass `csr_walk_test(..., warl_fields=[(name, lsb, width, reserved_value)])` — only the iterations that write the reserved value to a field switch that field to a masked compare plus a separate `*_<field>_legal` SIGUPD (e.g. senvcfg CBIE/PMM in `S.py`)
- Named splits: set `split_name` on a TestChunk to start a new named file group (`{suite}_{Name}-NN.S`). Later unnamed chunks stay in that group; length-based splitting still applies within it. Reusing a name non-contiguously raises. See `generate_ssstrict_suite` for the pattern.
- Priv tests are always config-dependent (use preprocessor conditionals for XLEN)
- Corresponding coverpoint `.svh` files in `coverpoints/priv/` are hand-written (not generated)
