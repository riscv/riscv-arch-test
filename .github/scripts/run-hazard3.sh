#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Run one ACT self-checking ELF on the Hazard3 Verilator testbench.
# Usage: run-hazard3.sh [--sim PATH] [--cycles N] [--timeout SEC] [--keep] --elf <path>
# Env:   HAZARD3_SIM  testbench executable (default: $HOME/repos/Hazard3-builds/bin/hazard3-tb)
#        CROSS        toolchain prefix (default: riscv64-unknown-elf)
set -uo pipefail

SIM="${HAZARD3_SIM:-$HOME/repos/Hazard3-builds/bin/hazard3-tb}"
CROSS="${CROSS:-riscv64-unknown-elf}"
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

# The testbench loads a flat binary at the base of RAM. With --cpuret, its exit status is
# the word the program writes to IO_EXIT, or 255 at the cycle limit.
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
