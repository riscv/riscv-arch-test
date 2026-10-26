#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
#
# Run one ACT ELF on the verilated BSC Sargantana core tile.
#
# Usage:  run-sargantana.sh [--tile DIR] [--max-cycles N] [--timeout SEC] --elf <path>
# Env:    SARGANTANA_TILE  core_tile checkout holding ./sim and ./bootrom.hex
#                          (default: ~/repos/core_tile)

set -uo pipefail

TILE="${SARGANTANA_TILE:-$HOME/repos/core_tile}"
# +max-cycles=0 runs forever, and the testbench's no-commit deadlock detector does not fire
# while a test spins on a load, so cap the run.
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

# The boot ROM jumps to 0x8000_0000, where the tests link. Its image path defaults to
# bootrom.hex in the working directory, so pass it explicitly.
out="$(timeout --foreground -k 5 "$TIMEOUT" \
  "$SIM" +bootrom="$TILE/bootrom.hex" +max-cycles="$MAX_CYCLES" +load="$ELF" 2>&1)"
rc=$?
printf '%s\n' "$out"

# Treat a failing tohost exit code as a failure even if the model exits 0.
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q 'Simulation ended with error code'; then
  rc=1
fi
exit $rc
