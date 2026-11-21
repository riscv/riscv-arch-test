#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Run one ACT self-checking ELF on a Chipyard Verilator simulator built by install-chipyard.sh.
#
# ACT4 tests self-check and print their verdict on the HTIF console, so this runner produces no
# signature. The ELF is preloaded into the simulated DRAM with +loadmem; fesvr still reads it to
# find tohost and fromhost, polls them over the serial-TileLink port, and turns the HTIF exit
# code into the simulator's exit status. A run that exceeds +max-cycles ends in $fatal.
# run_tests.py applies the wall-clock timeout and checks the exit status and RVCP-SUMMARY line.
#
# Usage:  run-chipyard.sh --elf <path-to-elf>
#   run_tests.py appends the ELF path as the final argument.
# Env:    CHIPYARD_SIM     path to the Chipyard simulator executable
#                          (default: simulator next to this script)
#         CHIPYARD_CYCLES  cycle limit (default: 60000000)
set -euo pipefail

SIM="${CHIPYARD_SIM:-$(dirname "${BASH_SOURCE[0]}")/simulator}"
CYCLES="${CHIPYARD_CYCLES:-60000000}"
[ "${1:-}" != --elf ] || shift
ELF="${1:?Usage: run-chipyard.sh --elf <path-to-elf>}"

if [ ! -x "$SIM" ]; then
  echo "run-chipyard.sh: no simulator at $SIM (build it with .github/scripts/install-chipyard.sh)" >&2
  exit 2
fi

exec "$SIM" +permissive +max-cycles="$CYCLES" +loadmem="$ELF" +permissive-off "$ELF" </dev/null
