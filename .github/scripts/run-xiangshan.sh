#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Run one ACT self-checking ELF on the XiangShan difftest emulator (Verilator), without a
# reference model.
#
# Usage:  run-xiangshan.sh [--emu PATH] [--cycles N] [--timeout SEC] --elf <path>
#   run_tests.py appends the ELF path as the final argument.
# Env:    XIANGSHAN_EMU       emulator binary (default: ~/repos/xiangshan-builds/bin/emu)
#         XIANGSHAN_CYCLES    cycle limit (default: 20000000)
#         XIANGSHAN_EMU_ARGS  extra emulator arguments
#         XIANGSHAN_TIMEOUT   wall-clock limit in seconds (default: 86400)
set -uo pipefail

EMU="${XIANGSHAN_EMU:-$HOME/repos/xiangshan-builds/bin/emu}"
CYCLES="${XIANGSHAN_CYCLES:-20000000}"
TIMEOUT="${XIANGSHAN_TIMEOUT:-86400}"
ELF=""

while [ $# -gt 0 ]; do
  case "$1" in
  --emu)
    EMU="$2"
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
  echo "run-xiangshan.sh: no ELF given" >&2
  exit 2
}
[ -f "$ELF" ] || {
  echo "run-xiangshan.sh: no such ELF: $ELF" >&2
  exit 2
}
[ -x "$EMU" ] || {
  echo "run-xiangshan.sh: no emulator at $EMU" >&2
  exit 2
}

# The emulator loads the ELF into simulated DRAM at 0x8000_0000; the default flash image at
# the reset vector jumps there. UART output and the emulator's status lines share stdout. The
# [PERF ] counter dump printed at exit (tens of thousands of lines) is dropped.
logfile="$(mktemp)"
trap 'rm -f "$logfile"' EXIT
# shellcheck disable=SC2086 # XIANGSHAN_EMU_ARGS is a list of arguments
timeout --foreground -k 5 "$TIMEOUT" "$EMU" -i "$ELF" --no-diff -C "$CYCLES" ${XIANGSHAN_EMU_ARGS:-} >"$logfile" 2>&1
rc=$?
out="$(sed '/^\[PERF \]/d' "$logfile")"
printf '%s\n' "$out"

# The emulator exits 0 on a cycle-limit timeout as well as on a good trap, so only an explicit
# HIT GOOD TRAP counts as a clean end of simulation.
case $out in
*"HIT GOOD TRAP"*) ;;
*)
  echo "run-xiangshan.sh: simulation did not end on a good trap (treated as a failure)" >&2
  [ "$rc" -ne 0 ] || rc=1
  ;;
esac
case $out in
*"CRITICAL ERROR"* | *"EXCEEDING CYCLE/INSTR LIMIT"*)
  echo "run-xiangshan.sh: critical error or $CYCLES-cycle limit (treated as a failure)" >&2
  [ "$rc" -ne 0 ] || rc=1
  ;;
esac

exit "$rc"
