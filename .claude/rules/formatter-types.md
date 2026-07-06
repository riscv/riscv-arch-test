---
paths:
  - "generators/testgen/src/testgen/formatters/types/**/*.py"
---

These are instruction type formatters, auto-discovered by the registry.

Key conventions:
- Use `@add_instruction_formatter("TYPE", config)` decorator from `testgen.formatters.registry`
- Define `InstructionTypeConfig` with required_params, reg_range, imm_bits, etc.
- Function signature: `(instr_name: str, test_data: TestData, params: InstructionParams) -> tuple[list[str], list[str], list[str]]`
- Returns `(setup_lines, test_lines, check_lines)`
- Use `load_int_reg()` for register setup, `write_sigupd()` for signature updates
- Each formatter also needs a `sample_TYPE.sv` template in `generators/coverage/src/covergroupgen/templates/`
