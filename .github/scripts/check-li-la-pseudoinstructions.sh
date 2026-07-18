#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
set -euo pipefail

pattern='(^|[ \t:;"'"'"'])[Ll][Ii][ \t](?!\()|(^|[ \t:;"'"'"'])[Ll][Aa][ \t](?!\()'

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  red='\033[31m'
  bold='\033[1m'
  reset='\033[0m'
else
  red=''
  bold=''
  reset=''
fi

found=0
for f in "$@"; do
  matches=$(grep -nP "$pattern" "$f" || true)
  if [ -n "$matches" ]; then
    found=1
    while IFS= read -r line; do
      echo "$f:$line"
    done <<< "$matches"
  fi
done

if [ "$found" -ne 0 ]; then
  echo
  echo "${bold}${red}error:${reset} disallowed 'li'/'la' assembler pseudoinstruction found above."
  echo "  Use 'LI(reg, imm)' or 'LA(reg, label)' macros instead (defined in tests/env/utils.h)."
  exit 1
fi
