#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
#
# Run one ACT ELF on a verilated XuanTie OpenC910 SoC.
#
# Usage:  run-c910.sh [--snapshot DIR] [--timeout SEC] [--keep] --elf <path>
#   run_tests.py appends the ELF path as the final argument.
# Env:    C910_SNAPSHOT  directory holding obj_dir/Vtop
#         CROSS          toolchain prefix (default: riscv64-unknown-elf)
set -uo pipefail

SNAPSHOT="${C910_SNAPSHOT:-}"
CROSS="${CROSS:-riscv64-unknown-elf}"
TIMEOUT=1200
KEEP=0
ELF=""

while [ $# -gt 0 ]; do
  case "$1" in
  --snapshot)
    SNAPSHOT="$2"
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
  echo "run-c910.sh: no ELF given" >&2
  exit 2
}
[ -f "$ELF" ] || {
  echo "run-c910.sh: no such ELF: $ELF" >&2
  exit 2
}

SIM="$SNAPSHOT/obj_dir/Vtop"
[ -x "$SIM" ] || {
  echo "run-c910.sh: no simulator at $SIM (set C910_SNAPSHOT; build with .github/scripts/install-c910.sh)" >&2
  exit 2
}
SIM_ABS="$(readlink -f "$SIM")"

# The testbench reads mem.pat from, and writes run_case.report to, its working directory.
WORK="${ELF%.elf}.c910run"
rm -rf "$WORK"
mkdir -p "$WORK" || exit 2

# mem.pat holds one 32-bit hex word per line with the lowest address in the most
# significant byte, so hexdump the flat image in address order.
"$CROSS-objcopy" -O binary --gap-fill 0 "$ELF" "$WORK/image.bin" || exit 2
od -An -tx1 -v -w4 "$WORK/image.bin" | tr -d ' ' | grep -v '^$' >"$WORK/mem.pat" || exit 2
rm -f "$WORK/image.bin"

out="$(cd "$WORK" && timeout --foreground -k 5 "$TIMEOUT" "$SIM_ABS" 2>&1)"
simrc=$?
printf '%s\n' "$out"

# Vtop always exits 0. The testbench writes run_case.report on the halt store.
report=""
[ -f "$WORK/run_case.report" ] && report="$(cat "$WORK/run_case.report")"

rc=0
if [ "$simrc" -ne 0 ]; then
  echo "run-c910.sh: simulator exited $simrc (timeout is ${TIMEOUT}s)" >&2
  rc=1
fi
if [ "$report" != "TEST PASS" ]; then
  echo "run-c910.sh: run_case.report is \"${report:-<missing>}\", not \"TEST PASS\" (hang, cycle cap, or RVMODEL_HALT_FAIL)" >&2
  rc=1
fi

others=$(printf '%s' "$out" | grep -c 'RVCP-SUMMARY: TEST \(FAILED\|SIGRUN\)' || true)
if [ "$others" -ne 0 ]; then
  rc=1
fi
# The testbench console occasionally drops a character, so a missing PASSED line is
# only reported.
passes=$(printf '%s' "$out" | grep -c 'RVCP-SUMMARY: TEST PASSED' || true)
if [ "$rc" -eq 0 ] && [ "$passes" -eq 0 ]; then
  echo "run-c910.sh: run_case.report says TEST PASS but no intact RVCP-SUMMARY line reached the console (dropped console byte)" >&2
fi

if [ "$rc" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
  rm -rf "$WORK"
else
  echo "run-c910.sh: artifacts kept in $WORK (exit $rc)" >&2
fi
exit $rc
