#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Run one ACT self-checking ELF on the Chipyard Verilator simulator (Rocket + Saturn + H).
#
# ACT4 tests self-check and print their verdict on the HTIF console, so this runner produces no
# signature. The ELF is preloaded into the simulated DRAM with +loadmem; fesvr still reads it to
# find tohost and fromhost, polls them over the serial-TileLink port, and turns the HTIF exit
# code into the simulator's exit status. A run that exceeds +max-cycles ends in $fatal.
#
# The verdict needs a zero exit status and a PASSED summary line, so a hang, a timeout or a
# crash can never be scored as a pass.
#
# Usage:  run-rocket.sh [--sim PATH] [--cycles N] [--timeout SEC] <path-to-elf>
#   run_tests.py appends the ELF path as the final argument.
# Env:    ROCKET_SIM     path to the Chipyard simulator executable
#                        (default: $HOME/repos/chipyard-builds/bin/simulator-rocket-saturn-h)
#         ROCKET_CYCLES  cycle limit (default: 60000000)
set -uo pipefail

SIM="${ROCKET_SIM:-$HOME/repos/chipyard-builds/bin/simulator-rocket-saturn-h}"
CYCLES="${ROCKET_CYCLES:-60000000}"
TIMEOUT=7200
ELF=""

while [ $# -gt 0 ]; do
  case "$1" in
  --sim)
    SIM="$2"
    shift 2
    ;;
  --cycles)
    CYCLES="$2"
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

if [ -z "$ELF" ]; then
  echo "run-rocket.sh: no ELF given" >&2
  exit 2
fi
if [ ! -f "$ELF" ]; then
  echo "run-rocket.sh: no such ELF: $ELF" >&2
  exit 2
fi
if [ ! -x "$SIM" ]; then
  echo "run-rocket.sh: no simulator at $SIM (build it with .github/scripts/install-rocket.sh)" >&2
  exit 2
fi

out="$(timeout --foreground -k 5 "$TIMEOUT" "$SIM" +permissive +max-cycles="$CYCLES" +loadmem="$ELF" \
  +permissive-off "$ELF" </dev/null 2>&1)"
rc=$?
printf '%s\n' "$out"

case $out in
*"RVCP-SUMMARY: TEST PASSED"*) ;;
*)
  echo "run-rocket.sh: no PASSED summary line (exit $rc)" >&2
  [ "$rc" -ne 0 ] || rc=1
  ;;
esac
case $out in
*"(timeout)"*)
  echo "run-rocket.sh: hit the $CYCLES-cycle limit" >&2
  [ "$rc" -ne 0 ] || rc=1
  ;;
esac
exit $rc
