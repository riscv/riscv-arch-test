#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Run one ACT self-checking ELF on lowRISC Ibex in Ibex Simple System under Verilator.
# Usage: run-ibex.sh [--snapshot DIR] [--cycles N] [--timeout SEC] [--keep] --elf <path>
# Env:   IBEX_SNAPSHOT  FuseSoC build root holding the simulator
#                       (default: ~/repos/ibex-builds/ot-rv32i)
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

# simulator_ctrl writes the console to ibex_simple_system.log in the current directory, so
# every test needs its own directory to run in parallel.
WORK="${ELF%.elf}.ibexrun"
rm -rf "$WORK"
mkdir -p "$WORK" || exit 2

ELF_ABS="$(readlink -f "$ELF")"
SIM_ABS="$(readlink -f "$SIM")"

# Discard the per-instruction trace, which runs to hundreds of MB.
ln -sf /dev/null "$WORK/trace_core_00000000.log"

simout="$(cd "$WORK" && timeout --foreground -k 5 "$TIMEOUT" "$SIM_ABS" --load-elf="$ELF_ABS" -c "$CYCLES" 2>&1)"
simrc=$?

console=""
if [ -f "$WORK/ibex_simple_system.log" ]; then
  console="$(cat "$WORK/ibex_simple_system.log")"
fi

printf '%s\n' "$console"
printf '%s\n' "$simout"

# The simulator exits 0 on every halt and at the -c cycle limit, so the verdict comes from
# the console.
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
  echo "run-ibex.sh: no RVCP-SUMMARY line in ibex_simple_system.log (hang, cycle limit, or crash)" >&2
  rc=1
fi

if [ "$rc" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
  rm -rf "$WORK"
else
  echo "run-ibex.sh: artifacts kept in $WORK (exit $rc)" >&2
fi
exit $rc
