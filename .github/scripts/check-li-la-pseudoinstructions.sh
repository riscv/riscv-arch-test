#!/usr/bin/env bash
# check-li-la-pseudoinstructions.sh
#
# SPDX-License-Identifier: Apache-2.0
#
# Pre-commit hook: fail if the `li` or `la` assembler pseudoinstructions are
# used. Both expand to a variable number of instructions depending on the
# value/address being materialized, which makes code sizes and branch offsets
# target-dependent. This repo requires the fixed-length `LI(reg, imm)` and
# `LA(reg, label)` macros from tests/env/utils.h instead.
#
# Usage: check-li-la-pseudoinstructions.sh <file>...

set -euo pipefail

# Match `li`/`la` as a standalone mnemonic. The negative lookahead lets the
# uppercase LI()/LA() macros through, including when written as `LI (reg, imm)`.
pattern='(^|[[:space:];:"'"'"'])(li|la)(?![[:space:]]*\()[[:space:]]'

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
  red=$'\033[31m'
  bold=$'\033[1m'
  reset=$'\033[0m'
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
  echo "${bold}${red}error:${reset} disallowed li/la assembler pseudoinstruction found above."
  echo "  Use 'LI(reg, imm)' or 'LA(reg, label)' from tests/env/utils.h instead."
  exit 1
fi
