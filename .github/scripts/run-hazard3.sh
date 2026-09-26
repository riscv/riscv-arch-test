#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Run one ACT self-checking ELF on the verilated Hazard3 testbench.
#
# ACT4 tests self-check and report by printing to the console, so this runner produces no
# signature: it converts the ELF to the flat binary the testbench loads, runs the model, and
# lets the RVCP-SUMMARY line reach stdout where run_tests.py parses it.
#
# The testbench loads a flat binary at MEM_BASE (0x8000_0000) rather than an ELF, and with
# --cpuret its process exit status is the word the CPU wrote to IO_EXIT, so RVMODEL_HALT_PASS
# (0) and RVMODEL_HALT_FAIL (1) pass straight through and no log scraping is needed. A run
# that hits the cycle limit returns 255.
#
# Usage:  run-hazard3.sh [--sim PATH] [--cycles N] [--timeout SEC] [--keep] <path-to-elf>
#   run_tests.py appends the ELF path as the final argument.
# Env:    HAZARD3_SIM  path to the verilated testbench executable
#                      (default: $HOME/repos/Hazard3-builds/bin/hazard3-tb)
#         CROSS        toolchain prefix (default: riscv64-unknown-elf)
set -uo pipefail

SIM="${HAZARD3_SIM:-$HOME/repos/Hazard3-builds/bin/hazard3-tb}"
CROSS="${CROSS:-riscv64-unknown-elf}"
# 50 M cycles at the model's ~1.3 M cycles/s is ~40 s of wall time, and the longest ACT test
# measured on this core is far below it.
CYCLES=50000000
TIMEOUT=300
KEEP=0
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

if [ -z "$ELF" ]; then
  echo "run-hazard3.sh: no ELF given" >&2
  exit 2
fi
if [ ! -f "$ELF" ]; then
  echo "run-hazard3.sh: no such ELF: $ELF" >&2
  exit 2
fi
if [ ! -x "$SIM" ]; then
  echo "run-hazard3.sh: no simulator at $SIM (build it with .github/scripts/install-hazard3.sh)" >&2
  exit 2
fi

BIN="${ELF%.elf}.h3bin"
if ! "$CROSS-objcopy" -O binary "$ELF" "$BIN"; then
  echo "run-hazard3.sh: objcopy failed for $ELF" >&2
  exit 2
fi

out="$(timeout --foreground -k 5 "$TIMEOUT" "$SIM" --bin "$BIN" --cycles "$CYCLES" --cpuret 2>&1)"
rc=$?
printf '%s\n' "$out"

if [ "$rc" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
  rm -f "$BIN"
else
  echo "run-hazard3.sh: binary kept at $BIN (exit $rc)" >&2
fi
exit $rc
