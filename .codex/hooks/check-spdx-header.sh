#!/bin/bash
# Warn if a newly written Python file is missing the SPDX license header.
# SPDX-License-Identifier: Apache-2.0

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# Only check Python files
if [[ "$FILE_PATH" == *.py ]]; then
  if [[ -f "$FILE_PATH" ]]; then
    if ! head -10 "$FILE_PATH" | grep -q "SPDX-License-Identifier"; then
      echo '{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "WARNING: This Python file is missing the SPDX-License-Identifier header. Add: # SPDX-License-Identifier: Apache-2.0"}}'
      exit 0
    fi
  fi
fi

exit 0
