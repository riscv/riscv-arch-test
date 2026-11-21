#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Run one ACT self-checking ELF on the NEORV32 Verilator testbench (neorv32-act-tb.sv).
# The testbench exits 0 when the test writes 0 to its exit register and fails on any other exit
# value or at its cycle limit. run_tests.py applies the wall-clock timeout and checks the exit
# status and the RVCP-SUMMARY line.
# Usage: run-neorv32.sh --elf <path>
# Env:   NEORV32_SIM  testbench executable (default: neorv32-tb next to this script)
#        CROSS        toolchain prefix (default: riscv64-unknown-elf)
set -euo pipefail

SIM="${NEORV32_SIM:-$(dirname "${BASH_SOURCE[0]}")/neorv32-tb}"
CROSS="${CROSS:-riscv64-unknown-elf}"
[ "${1:-}" != --elf ] || shift
ELF="${1:?Usage: run-neorv32.sh --elf <path-to-elf>}"

if [ ! -x "$SIM" ]; then
  echo "run-neorv32.sh: no simulator at $SIM (build it with .github/scripts/install-neorv32.sh)" >&2
  exit 2
fi

# The testbench loads RAM from one 32-bit little-endian hex word per line, starting at the base
# of RAM (0x80000000), which is where the ELF is linked.
HEX="$(mktemp)"
trap 'rm -f "$HEX" "$HEX.bin"' EXIT
"$CROSS-objcopy" -O binary "$ELF" "$HEX.bin"
od -An -v -tx4 -w4 "$HEX.bin" | tr -d ' ' >"$HEX"
"$SIM" "+MEM=$HEX" </dev/null
