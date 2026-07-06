#!/bin/bash
# Block direct python/python3 invocation — use uv run instead.
# SPDX-License-Identifier: Apache-2.0

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

# Check if command starts with python or python3 (but not uv run python)
if echo "$COMMAND" | grep -qE '^\s*(python3?|\.venv/bin/python)\b' && ! echo "$COMMAND" | grep -qE '^\s*uv\s+run'; then
  echo "BLOCKED: Do not invoke python directly. Use 'uv run' instead." >&2
  echo "Example: uv run python script.py  or  uv run testgen ..." >&2
  exit 2
fi

exit 0
