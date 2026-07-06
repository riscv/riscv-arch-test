---
paths:
  - "generators/coverage/**"
---

# covergroupgen Package Reference

Generates SystemVerilog covergroup files (`.svh`) from `.sv` templates + CSV testplans. Output goes to `coverpoints/unpriv/` (generated, do not edit).

## Templates (`templates/`)

- `cp_*.sv` — Coverpoint definitions. One per coverpoint name.
- `sample_*.sv` — Instruction sampling. One per instruction type.
- `header.sv`, `end.sv` — Wrapper boilerplate.
- `init.sv`, `coverageinit.sv` — Initialization.
- `vector/` — SEW-dependent and widening variants.

## Key Concepts

- **SEW-dependent coverpoints**: Vary by element width. Listed in `SEW_DEPENDENT_CPS` in `generate.py`.
- **Vector expansion**: Vx -> Vx8, Vx16, Vx32, Vx64.
- **E extension**: I testplan duplicated as E.
