#!/usr/bin/env bash
# check-align-directive.sh
#
# Jordan Carlin jcarlin@hmc.edu July 2026
# SPDX-License-Identifier: Apache-2.0
#
# Pre-commit hook: fail if the ambiguous `.align` assembler directive is used.
# `.align`'s alignment unit (bytes vs. power-of-two exponent) is target-
# dependent, so this repo requires the unambiguous `.p2align N` (align to
# 2^N bytes) or `.balign N` (align to N bytes) instead.
#
# Usage: check-align-directive.sh <file>...

set -euo pipefail

pattern='(^|[[:space:];:"'"'"'])\.align([[:space:]]|$)'

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
  matches=$(grep -nE "$pattern" "$f" || true)
  if [ -n "$matches" ]; then
    found=1
    while IFS= read -r line; do
      echo "$f:$line"
    done <<<"$matches"
  fi
done

if [ "$found" -ne 0 ]; then
  echo
  echo "${bold}${red}error:${reset} disallowed '.align' assembler directive found above."
  echo "  Use '.p2align N' (align to 2^N bytes) or '.balign N' (align to N bytes) instead."
  exit 1
fi
