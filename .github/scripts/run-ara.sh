#!/usr/bin/env bash
# Run one ACT self-checking ELF on the verilated CVA6 + Ara model.
#
# ACT4 tests self-check and report by printing to the console, so this runner does not
# produce or compare a signature: it loads the ELF, runs the testbench, and lets the
# RVCP-SUMMARY line reach stdout where run_tests.py parses it.
#
# Usage:  run-ara.sh [--snapshot DIR] [--cycles N] [--timeout SEC] --elf <path>
#   run_tests.py appends the ELF path as the final argument.
# Env:    ARA_SNAPSHOT  directory holding verilator/Vara_tb_verilator
#                       (default: ~/repos/ara-builds/hier4v512)
#         ARA_CYCLES    testbench cycle limit (default: 20000000)
set -uo pipefail

SNAPSHOT="${ARA_SNAPSHOT:-$HOME/repos/ara-builds/hier4v512}"
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
  echo "run-ara.sh: no simulator at $SIM (build it with hardware/Makefile verilate)" >&2
  exit 2
}

# The testbench loads the ELF directly by its program headers into the "ram" memory
# area, which is the L2 at 0x8000_0000 - the same address the reset vector points at,
# so no boot stub and no objcopy are needed. Note that -c must precede -l, because
# the memory-init option parser consumes the next argument unconditionally.
out="$(timeout --foreground -k 5 "$TIMEOUT" "$SIM" -c "$CYCLES" -l "ram,$ELF,elf" 2>&1)"
rc=$?
printf '%s\n' "$out"

# A cycle-limit timeout prints this message and still exits 0, so it has to be turned
# into a failure explicitly or every hung test would be scored as a pass.
if printf '%s' "$out" | grep -q 'Simulation timeout of'; then
  echo "run-ara.sh: testbench hit its $CYCLES-cycle limit (treated as a failure)" >&2
  rc=1
fi

# The exit code is (exit_o >> 1) from the control register, so a test that stores 1
# would exit 0. The console verdict is authoritative; trust it when it is present.
if printf '%s' "$out" | grep -q 'RVCP-SUMMARY: TEST FAILED'; then
  rc=1
fi

exit $rc
