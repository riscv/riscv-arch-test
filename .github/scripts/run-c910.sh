#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Run one ACT self-checking ELF on a verilated XuanTie OpenC910 SoC.
#
# ACT4 tests self-check and report by printing to the console, so this runner does not
# produce or compare a signature. Three OpenC910 facts shape it:
#
#   1. The testbench loads "mem.pat" from the CURRENT DIRECTORY and writes
#      "run_case.report" there, so every test needs its own directory.
#   2. mem.pat is a $readmemh file of 32-bit words in which the MOST significant byte
#      is the LOWEST address (ram0 of the 16-byte-wide SRAM holds bits [31:24]).  That
#      is the opposite of the little-endian word value, so the image is produced with
#      objcopy -O binary and hexdumped in address order, not with objcopy -O verilog.
#   3. The simulator ALWAYS exits 0 - sim_main1.cpp returns 0 unconditionally and both
#      halt paths reach it through $finish. The verdict therefore comes from
#      run_case.report, which the testbench writes on the halt store, and the file is
#      deleted first so that a timeout, a hang or a crash cannot look like a pass.
#      The console RVCP-SUMMARY line is used only as a cross-check for an explicit
#      failure, NOT as the pass condition: the testbench's character output drops or
#      mangles roughly one byte in every few hundred tests (measured: 1 corrupted
#      summary line in 538 runs), so requiring an intact "TEST PASSED" string would
#      turn that into a spurious failure. RVMODEL_HALT_PASS is only reached after the
#      test's own self-check has passed, so the report is the authoritative verdict.
#
# Usage:  run-c910.sh [--snapshot DIR] [--timeout SEC] [--keep] --elf <path>
#   run_tests.py appends the ELF path as the final argument.
# Env:    C910_SNAPSHOT  directory holding obj_dir/Vtop
#                        (default: ~/repos/openc910/smart_run/work)
#         CROSS          toolchain prefix (default: riscv64-unknown-elf)
set -uo pipefail

SNAPSHOT="${C910_SNAPSHOT:-$HOME/repos/openc910/smart_run/work}"
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
  echo "run-c910.sh: no simulator at $SIM (build it with .github/scripts/install-c910.sh)" >&2
  exit 2
}
SIM_ABS="$(readlink -f "$SIM")"

WORK="${ELF%.elf}.c910run"
rm -rf "$WORK"
mkdir -p "$WORK" || exit 2

# The image is a flat binary starting at address 0 (link.ld puts the reset trampoline
# there), emitted as one 32-bit hex word per line with byte 0 in the top nibble pair.
"$CROSS-objcopy" -O binary --gap-fill 0 "$ELF" "$WORK/image.bin" || exit 2
od -An -tx1 -v -w4 "$WORK/image.bin" | tr -d ' ' | grep -v '^$' >"$WORK/mem.pat" || exit 2
rm -f "$WORK/image.bin"

out="$(cd "$WORK" && timeout --foreground -k 5 "$TIMEOUT" "$SIM_ABS" 2>&1)"
simrc=$?
printf '%s\n' "$out"

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
