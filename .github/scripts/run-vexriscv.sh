#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Run one ACT self-checking ELF on the VexRiscv Verilator testbench (vexriscv-tb.cpp).
# The testbench loads the ELF itself; its exit status is the word the test writes to the exit
# register, or 3 at the cycle limit. run_tests.py applies the wall-clock timeout and checks the
# exit status and the RVCP-SUMMARY line.
# Usage: run-vexriscv.sh --elf <path>
# Env:   VEXRISCV_SIM     testbench executable (default: $HOME/repos/vexriscv-builds/bin/vexriscv-tb)
#        VEXRISCV_CYCLES  cycle limit (default: 50000000)
set -euo pipefail

SIM="${VEXRISCV_SIM:-$HOME/repos/vexriscv-builds/bin/vexriscv-tb}"
CYCLES="${VEXRISCV_CYCLES:-50000000}"
[ "${1:-}" != --elf ] || shift
ELF="${1:?Usage: run-vexriscv.sh --elf <path-to-elf>}"

if [ ! -x "$SIM" ]; then
  echo "run-vexriscv.sh: no simulator at $SIM (build it with .github/scripts/install-vexriscv.sh)" >&2
  exit 2
fi

exec "$SIM" "$ELF" +max-cycles="$CYCLES" </dev/null
