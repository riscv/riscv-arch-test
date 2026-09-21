#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Run one ACT self-checking ELF on a verilated lowRISC Ibex in Ibex Simple System.
#
# ACT4 tests self-check and report by printing to the console, so this runner does not
# produce or compare a signature. Two Ibex-specific facts shape it:
#
#   1. Console output goes to a FILE, not stdout. simulator_ctrl opens
#      "ibex_simple_system.log" relative to the current directory, so each test needs
#      its own directory, and the log has to be copied to stdout for run_tests.py to
#      find the RVCP-SUMMARY line.
#   2. The simulator ALWAYS exits 0. Pass and fail share the single halt path (a write
#      to SIM_CTRL), and hitting the -c cycle limit also exits 0. The verdict therefore
#      comes from the log: any "TEST FAILED"/"TEST SIGRUN" summary, or no summary at
#      all (a hang, a cycle-limit expiry, a wall-clock timeout, a crash), exits nonzero.
#
# Usage:  run-ibex.sh [--snapshot DIR] [--cycles N] [--timeout SEC] [--keep] --elf <path>
#   run_tests.py appends the ELF path as the final argument.
# Env:    IBEX_SNAPSHOT  directory holding the verilated simulator
#                        (default: ~/repos/ibex-builds/ot-rv32i)
set -uo pipefail

SNAPSHOT="${IBEX_SNAPSHOT:-$HOME/repos/ibex-builds/ot-rv32i}"
CYCLES=20000000
TIMEOUT=600
KEEP=0
ELF=""

while [ $# -gt 0 ]; do
  case "$1" in
  --snapshot)
    SNAPSHOT="$2"
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
  --keep)
    KEEP=1
    shift
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
  echo "run-ibex.sh: no ELF given" >&2
  exit 2
}
[ -f "$ELF" ] || {
  echo "run-ibex.sh: no such ELF: $ELF" >&2
  exit 2
}

SIM="$SNAPSHOT/lowrisc_ibex_ibex_simple_system_0/sim-verilator/Vibex_simple_system"
[ -x "$SIM" ] || {
  echo "run-ibex.sh: no simulator at $SIM (build it with .github/scripts/install-ibex.sh)" >&2
  exit 2
}

# simulator_ctrl hard-codes the log name relative to the current directory, so every
# test needs a private directory to run in parallel safely.
WORK="${ELF%.elf}.ibexrun"
rm -rf "$WORK"
mkdir -p "$WORK" || exit 2

ELF_ABS="$(readlink -f "$ELF")"
SIM_ABS="$(readlink -f "$SIM")"

# ibex_tracer writes one disassembled line per retired instruction to
# trace_core_00000000.log, which for a full ACT test is hundreds of MB and is never
# read. Point it at /dev/null; ibex_simple_system.log is what the verdict comes from.
ln -sf /dev/null "$WORK/trace_core_00000000.log"

simout="$(cd "$WORK" && timeout --foreground -k 5 "$TIMEOUT" "$SIM_ABS" --load-elf="$ELF_ABS" -c "$CYCLES" 2>&1)"
simrc=$?

console=""
if [ -f "$WORK/ibex_simple_system.log" ]; then
  console="$(cat "$WORK/ibex_simple_system.log")"
fi

# The console log carries the RVCP-SUMMARY line run_tests.py greps for; the simulator's
# own stdout carries the cycle counts and any $fatal message.
printf '%s\n' "$console"
printf '%s\n' "$simout"

rc=0
if [ "$simrc" -ne 0 ]; then
  echo "run-ibex.sh: simulator exited $simrc (timeout is ${TIMEOUT}s)" >&2
  rc=1
fi

passes=$(printf '%s' "$console" | grep -c 'RVCP-SUMMARY: TEST PASSED' || true)
others=$(printf '%s' "$console" | grep -c 'RVCP-SUMMARY: TEST \(FAILED\|SIGRUN\)' || true)
if [ "$others" -ne 0 ]; then
  rc=1
elif [ "$passes" -eq 0 ]; then
  # No summary at all: the test hung, hit the cycle limit, or died before printing.
  echo "run-ibex.sh: no RVCP-SUMMARY line in ibex_simple_system.log (hang, cycle limit, or crash)" >&2
  rc=1
fi

if [ "$rc" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
  rm -rf "$WORK"
else
  echo "run-ibex.sh: artifacts kept in $WORK (exit $rc)" >&2
fi
exit $rc
