#!/bin/bash
# Auto-format Python files after editing with ruff.
# SPDX-License-Identifier: Apache-2.0

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only process Python files
if [[ "$FILE_PATH" == *.py ]]; then
  # Skip files in excluded directories
  if [[ "$FILE_PATH" == *"/scripts/"* ]] || [[ "$FILE_PATH" == *"external/"* ]]; then
    exit 0
  fi
  uv run ruff format "$FILE_PATH" 2>/dev/null
  uv run ruff check --fix "$FILE_PATH" 2>/dev/null
fi

exit 0
