#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Run one ACT ELF on the verilated VeeR EH2 testbench.
#
# Usage:  run-veer-eh2.sh [--snapshot DIR] [--timeout SEC] [--keep] --elf <path>
# Env:    VEER_SNAPSHOT  directory holding obj_dir/Vtb_top   (default: ~/repos/veer-builds/eh2)
#         CROSS          toolchain prefix                    (default: riscv64-unknown-elf)
set -uo pipefail

SNAPSHOT="${VEER_SNAPSHOT:-$HOME/repos/veer-builds/eh2}"
CROSS="${CROSS:-riscv64-unknown-elf}"
TIMEOUT=280
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
  --elf) shift ;; # run_tests.py appends the ELF path after --elf
  *)
    ELF="$1"
    shift
    ;;
  esac
done

[ -n "$ELF" ] || {
  echo "run-veer-eh2.sh: no ELF given" >&2
  exit 2
}
[ -f "$ELF" ] || {
  echo "run-veer-eh2.sh: no such ELF: $ELF" >&2
  exit 2
}
SIM="$SNAPSHOT/obj_dir/Vtb_top"
[ -x "$SIM" ] || {
  echo "run-veer-eh2.sh: no simulator at $SIM (build it with tools/Makefile verilator-build)" >&2
  exit 2
}

# The testbench reads program.hex and writes console.log and exec.log in the current
# directory, so each test runs in its own directory.
WORK="${ELF%.elf}.veerrun"
rm -rf "$WORK"
mkdir -p "$WORK" || exit 2

"$CROSS-objcopy" -O verilog "$ELF" "$WORK/program.hex" || exit 2

# The testbench writes a trace line for every retired instruction; discard it.
ln -sf /dev/null "$WORK/exec.log"
ln -sf /dev/null "$WORK/trace_port.csv"

(cd "$WORK" && timeout --foreground -k 5 "$TIMEOUT" "$SIM" 2>&1)
rc=$?

if [ "$rc" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
  rm -rf "$WORK"
else
  echo "run-veer-eh2.sh: artifacts kept in $WORK (exit $rc)" >&2
fi
exit $rc
