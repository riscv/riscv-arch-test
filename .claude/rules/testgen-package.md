---
paths:
  - "generators/testgen/**"
---

# testgen Package Reference

The `testgen` CLI reads CSV testplans and generates RISC-V assembly test files. See `.claude/agents/` for step-by-step workflows.

## Key Entry Points

- `cli.py` — Typer CLI. Parallelizes across extensions with `ProcessPoolExecutor`.
- `generate/unpriv.py` — Unprivileged: reads CSV, calls coverpoint generators, splits into files.
- `generate/priv.py` — Privileged: calls priv generator, wraps in test file structure.

## Key Data Classes

- **`TestData`** (`data/state.py`): Mutable state. Manages register allocation, testcase counting, active `TestChunk`. Created per-instruction (unpriv) or per-feature (priv).
- **`TestChunk`** (`data/test_chunk.py`): Unsplittable group of testcases with code, data, and signature update count.
- **`TestConfig`** (`data/config.py`): Immutable config (xlen, flen, testsuite, E_ext).
- **`InstructionParams`** (`data/params.py`): Instruction operand values.

## Register Management

- `int_regs.get_registers(n)` — Allocate n registers.
- `int_regs.consume_registers([reg])` — Reserve specific register, returns relocation code.
- `int_regs.return_registers([reg])` — Return to pool.
- Use `return_test_regs(test_data, params)` helper after each testcase.
