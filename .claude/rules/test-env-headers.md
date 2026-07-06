---
paths:
  - "tests/env/**"
---

These are hand-written test infrastructure headers shared by all generated tests. Changes here affect every test.

Be extremely careful when modifying these files:

- `arch_test.h` and `test_macros.h` define core macros used by every generated test
- Changing macro signatures or behavior can break all test generation
- Test changes against both RV32 and RV64 configurations
- Test with both spike and sail configs if possible
- The generated `encoding.h` file contains RISC-V instruction encodings and should match the ISA spec
