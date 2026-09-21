#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Run one ACT self-checking ELF on the verilated BSC Sargantana core tile.
#
# ACT4 tests self-check and report by printing to the console, so this runner does not
# produce or compare a signature: it loads the ELF, runs the testbench, and lets the
# RVCP-SUMMARY line reach stdout where run_tests.py parses it.
#
# Usage:  run-sargantana.sh [--tile DIR] [--max-cycles N] [--timeout SEC] --elf <path>
#   run_tests.py appends the ELF path as the final argument.
# Env:    SARGANTANA_TILE  core_tile checkout holding ./sim and ./bootrom.hex
#                          (default: ~/repos/core_tile)

set -uo pipefail

TILE="${SARGANTANA_TILE:-$HOME/repos/core_tile}"
# The testbench has no default cycle cap (+max-cycles=0 means "run forever"), and its
# 200-cycle no-commit deadlock detector does not fire while a test spins on a load, so
# a cap is needed for a hung test to be reported rather than to wedge the shard.
MAX_CYCLES=3000000
TIMEOUT=600
ELF=""

while [ $# -gt 0 ]; do
  case "$1" in
  --tile)
    TILE="$2"
    shift 2
    ;;
  --max-cycles)
    MAX_CYCLES="$2"
    shift 2
    ;;
  --timeout)
    TIMEOUT="$2"
    shift 2
    ;;
  --elf)
    shift
    ;;
  *)
    ELF="$1"
    shift
    ;;
  esac
done

[ -n "$ELF" ] || {
  echo "run-sargantana.sh: no ELF given" >&2
  exit 2
}
[ -f "$ELF" ] || {
  echo "run-sargantana.sh: no such ELF: $ELF" >&2
  exit 2
}
SIM="$TILE/sim"
[ -x "$SIM" ] || {
  echo "run-sargantana.sh: no simulator at $SIM (build it with 'make sim' in core_tile)" >&2
  exit 2
}

# simulator/models/hdl/bootrom_behav.sv:21 defaults the bootrom image to the relative
# path "bootrom.hex", so it is passed explicitly and the runner needs no working
# directory of its own. The bootrom is what jumps to DRAM_BASE = 0x8000_0000, where the
# tests link; without it the core fetches from an empty ROM and the test simply times out.
out="$(timeout --foreground -k 5 "$TIMEOUT" \
  "$SIM" +bootrom="$TILE/bootrom.hex" +max-cycles="$MAX_CYCLES" +load="$ELF" 2>&1)"
rc=$?
printf '%s\n' "$out"

# l2_behav.sv:454 calls $finish for exit code 0 and $error otherwise, so a passing test
# already exits 0. Verilator's $error does not stop the model, so a failing test keeps
# running to the cycle cap; force a nonzero status from the console instead of relying on
# how that run happens to end.
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q 'Simulation ended with error code'; then
  rc=1
fi
exit $rc
