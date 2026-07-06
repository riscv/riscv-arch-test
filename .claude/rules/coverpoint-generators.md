---
paths:
  - "generators/testgen/src/testgen/coverpoints/**/*.py"
---

These are unprivileged coverpoint test generators, auto-discovered by the registry.

Key conventions:
- Use `@add_coverpoint_generator("cp_name")` decorator from `testgen.coverpoints.registry`
- Function signature: `(instr_name: str, instr_type: str, coverpoint: str, test_data: TestData) -> list[TestChunk]`
- Standard coverpoints use `format_single_testcase()` for one TestChunk per testcase
- Special coverpoints (in `special/`) use `begin_test_chunk()`/`end_test_chunk()` directly
- Always call `return_test_regs(test_data, params)` after each testcase to free registers
- Files starting with `_` are skipped during auto-discovery (use for helpers)
- Longest-prefix matching resolves decorator patterns, so `cp_rd_nx0` matches before `cp_rd`
