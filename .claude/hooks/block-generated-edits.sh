#!/bin/bash
# Block edits to generated files that will be overwritten by make tests.
# SPDX-License-Identifier: Apache-2.0

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Normalize to relative path from project root
PROJECT_DIR=$(echo "$INPUT" | jq -r '.cwd // empty')
if [[ -n "$PROJECT_DIR" && "$FILE_PATH" == "$PROJECT_DIR"* ]]; then
  FILE_PATH="${FILE_PATH#$PROJECT_DIR/}"
fi

# Generated file patterns (overwritten by make tests)
GENERATED_PATTERNS=(
  "tests/rv32i/"
  "tests/rv32e/"
  "tests/rv64i/"
  "tests/rv64e/"
  "tests/priv/"
  "coverpoints/unpriv/"
  "coverpoints/coverage/"
)

for pattern in "${GENERATED_PATTERNS[@]}"; do
  if [[ "$FILE_PATH" == $pattern* ]]; then
    echo "BLOCKED: '$FILE_PATH' is a generated file (overwritten by 'make tests'). Edit the generators instead:" >&2
    echo "  - Unprivileged tests: generators/testgen/src/testgen/coverpoints/ or testplans/*.csv" >&2
    echo "  - Privileged tests: generators/testgen/src/testgen/priv/extensions/" >&2
    echo "  - Coverage files: generators/coverage/src/covergroupgen/templates/" >&2
    exit 2
  fi
done

# Also block editing the auto-generated decode package
if [[ "$FILE_PATH" == *"RISCV_imported_decode_pkg.svh" ]]; then
  echo "BLOCKED: RISCV_imported_decode_pkg.svh is auto-generated. Do not edit." >&2
  exit 2
fi

exit 0
