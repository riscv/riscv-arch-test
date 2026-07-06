---
name: verify-ext
description: End-to-end verification of a RISC-V extension. Generates tests, compiles ELFs, and checks for errors. Use after adding or modifying an extension.
user-invocable: true
argument-hint: "[extension name, e.g. Zba]"
---

# Verify Extension End-to-End

Run the full pipeline for a specific extension to verify everything works.

## Steps

1. If no extension specified in $ARGUMENTS, ask the user
2. Run `make lint` to check for Python errors first
3. Generate tests: `EXTENSIONS=$ARGUMENTS make tests`
4. Compile ELFs: `EXTENSIONS=$ARGUMENTS make`
5. Report results:
   - Number of test files generated
   - Compilation success/failure
   - Any test failures (look for RVCP-SUMMARY lines)

## Troubleshooting

If test generation fails:

- Check that `testplans/$ARGUMENTS.csv` exists
- Check that all coverpoint generators referenced in the CSV are registered
- Check that the instruction type formatters are registered

If compilation fails:

- Check compiler errors in the build output
- Look for undefined macros or missing includes
- Verify the test assembly syntax is correct

If tests fail:

- Check for configuration mismatch
- Look at the objdump to understand test behavior
- Verify Sail model config matches
