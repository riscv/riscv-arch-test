#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
#
# Run one ACT ELF on a verilated XuanTie OpenE902 smart_run SoC.
#
# Usage:  run-e902.sh [--snapshot DIR] [--timeout SEC] [--keep] --elf <path>
#   run_tests.py appends the ELF path as the final argument.
# Env:    E902_SNAPSHOT  directory holding obj_dir/Vtb
#         CROSS          toolchain prefix (default: riscv64-unknown-elf)
set -uo pipefail

SNAPSHOT="${E902_SNAPSHOT:-}"
CROSS="${CROSS:-riscv64-unknown-elf}"
TIMEOUT=600
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
  echo "run-e902.sh: no ELF given" >&2
  exit 2
}
[ -f "$ELF" ] || {
  echo "run-e902.sh: no such ELF: $ELF" >&2
  exit 2
}

SIM="$SNAPSHOT/obj_dir/Vtb"
[ -x "$SIM" ] || {
  echo "run-e902.sh: no simulator at $SIM (set E902_SNAPSHOT; build with .github/scripts/install-e902.sh)" >&2
  exit 2
}
SIM_ABS="$(readlink -f "$SIM")"

# The testbench reads mem.pat from, and writes run_case.report to, its working directory.
WORK="${ELF%.elf}.e902run"
rm -rf "$WORK"
mkdir -p "$WORK" || exit 2

# mem.pat holds one 32-bit hex word per line with the lowest address in the most
# significant byte, so hexdump the flat image in address order.  The image starts at
# address 0 and must fit in the 512 KB instruction-bus SRAM.
"$CROSS-objcopy" -O binary --gap-fill 0 "$ELF" "$WORK/image.bin" || exit 2
size=$(stat -c %s "$WORK/image.bin")
if [ "$size" -gt 524288 ]; then
  echo "run-e902.sh: image is $size bytes, larger than the 512 KB SRAM" >&2
  exit 2
fi
# Pad the image to whole words: od prints a short last line, which $readmemh would read as
# a right-justified word and so load into the wrong bytes.
truncate -s %4 "$WORK/image.bin" || exit 2
od -An -tx1 -v -w4 "$WORK/image.bin" | tr -d ' ' | grep -v '^$' >"$WORK/mem.pat" || exit 2
rm -f "$WORK/image.bin"

out="$(cd "$WORK" && timeout --foreground -k 5 "$TIMEOUT" "$SIM_ABS" 2>&1)"
simrc=$?
printf '%s\n' "$out"

# Vtb exits 0 on every $finish.  The testbench writes the verdict to run_case.report:
# TEST PASS on RVMODEL_HALT_PASS, TEST FAIL on RVMODEL_HALT_FAIL, the cycle cap, or
# 5000 cycles without a retired instruction.
report=""
[ -f "$WORK/run_case.report" ] && report="$(tr -d '\n' <"$WORK/run_case.report")"

rc=0
if [ "$simrc" -ne 0 ]; then
  echo "run-e902.sh: simulator exited $simrc (timeout is ${TIMEOUT}s)" >&2
  rc=1
fi
if [ "$report" != "TEST PASS" ]; then
  echo "run-e902.sh: run_case.report is \"${report:-<missing>}\", not \"TEST PASS\" (hang, cycle cap, or RVMODEL_HALT_FAIL)" >&2
  rc=1
fi
case $out in
*"RVCP-SUMMARY: TEST FAILED"* | *"RVCP-SUMMARY: TEST SIGRUN"*) rc=1 ;;
*"RVCP-SUMMARY: TEST PASSED"*) ;;
*) echo "run-e902.sh: warning: no RVCP-SUMMARY line on the console" >&2 ;;
esac

if [ "$rc" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
  rm -rf "$WORK"
else
  echo "run-e902.sh: artifacts kept in $WORK (exit $rc)" >&2
fi
exit $rc
