#!/bin/bash
# Run pyright on edited Python files and surface type errors to Claude.
# SPDX-License-Identifier: Apache-2.0

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ "$FILE_PATH" != *.py ]]; then
  exit 0
fi

if [[ "$FILE_PATH" == *"/scripts/"* ]] || [[ "$FILE_PATH" == *"external/"* ]]; then
  exit 0
fi

if [[ ! -f "$FILE_PATH" ]]; then
  exit 0
fi

if ! OUTPUT=$(uv run pyright "$FILE_PATH" 2>&1); then
  MESSAGE="pyright reported type errors in $FILE_PATH:"$'\n'"$OUTPUT"
  jq -n --arg msg "$MESSAGE" '{hookSpecificOutput: {hookEventName: "PostToolUse", additionalContext: $msg}}'
fi

exit 0
