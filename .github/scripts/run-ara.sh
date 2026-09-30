#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Run one ACT ELF on the verilated CVA6 + Ara model.
# Usage: run-ara.sh [--snapshot DIR] [--cycles N] [--timeout SEC] --elf <path>
# Env:   ARA_SNAPSHOT  directory holding verilator/Vara_tb_verilator
#                      (default: ~/repos/ara-builds/build)
#        ARA_CYCLES    testbench cycle limit (default: 20000000)
set -uo pipefail

SNAPSHOT="${ARA_SNAPSHOT:-$HOME/repos/ara-builds/build}"
CYCLES="${ARA_CYCLES:-20000000}"
TIMEOUT=3600
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
  echo "run-ara.sh: no ELF given" >&2
  exit 2
}
[ -f "$ELF" ] || {
  echo "run-ara.sh: no such ELF: $ELF" >&2
  exit 2
}
SIM="$SNAPSHOT/verilator/Vara_tb_verilator"
[ -x "$SIM" ] || {
  echo "run-ara.sh: no simulator at $SIM (build it with install-ara.sh)" >&2
  exit 2
}

# The testbench writes trace_hart_0.dasm to its working directory, so give each run its own.
ELF="$(realpath "$ELF")"
RUNDIR="$(mktemp -d)"
trap 'rm -rf "$RUNDIR"' EXIT

# -c must precede -l: the memory-init option parser consumes the next argument.
out="$(cd "$RUNDIR" && timeout --foreground -k 5 "$TIMEOUT" "$SIM" -c "$CYCLES" -l "ram,$ELF,elf" 2>&1)"
rc=$?
printf '%s\n' "$out"

# The testbench exits 0 when it reaches its cycle limit.
if printf '%s' "$out" | grep -q 'Simulation timeout of'; then
  echo "run-ara.sh: testbench hit its $CYCLES-cycle limit (treated as a failure)" >&2
  rc=1
fi

# The exit code is the stored value >> 1, so the console verdict decides.
if printf '%s' "$out" | grep -q 'RVCP-SUMMARY: TEST FAILED'; then
  rc=1
fi

exit $rc
