---
name: gen-tests
description: Generate test assembly files for specific extensions. Use when you've modified coverpoint generators, formatters, or priv extensions and want to verify output.
user-invocable: true
argument-hint: "[extensions: comma-separated, e.g. I,M,Zba]"
---

# Generate Tests

Regenerate test assembly files for the specified extensions.

## Steps

1. If no extensions specified in $ARGUMENTS, ask the user which extensions to generate
2. Clean existing generated tests: `make clean-tests`
3. Generate tests: `EXTENSIONS=$ARGUMENTS make tests`
4. Report the number of test files generated per extension
5. If generation fails, read the error output and diagnose the issue

## Common Issues

- Missing coverpoint generator: Check that all coverpoint columns in the CSV have registered `@add_coverpoint_generator` handlers
- Missing instruction formatter: Check that the `Type` column in the CSV matches a registered `@add_instruction_formatter`
- Import errors: Run `make lint` to catch type/import issues
