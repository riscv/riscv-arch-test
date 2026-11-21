#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Run one ACT self-checking ELF on the NEORV32 Verilator testbench.
# Usage: run-neorv32.sh [--sim PATH] [--cycles N] [--timeout SEC] [--keep] --elf <path>
# Env:   NEORV32_SIM  testbench executable (default: $HOME/repos/neorv32-builds/bin/neorv32-tb)
#        CROSS        toolchain prefix (default: riscv64-unknown-elf)
set -uo pipefail

SIM="${NEORV32_SIM:-$HOME/repos/neorv32-builds/bin/neorv32-tb}"
CROSS="${CROSS:-riscv64-unknown-elf}"
CYCLES=50000000
TIMEOUT=600
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
  echo "run-neorv32.sh: no ELF given" >&2
  exit 2
fi
if [ ! -f "$ELF" ]; then
  echo "run-neorv32.sh: no such ELF: $ELF" >&2
  exit 2
fi
if [ ! -x "$SIM" ]; then
  echo "run-neorv32.sh: no simulator at $SIM (build it with .github/scripts/install-neorv32.sh)" >&2
  exit 2
fi

# The testbench loads RAM from one 32-bit little-endian hex word per line, starting at the base
# of RAM (0x80000000), which is where the ELF is linked.
BIN="${ELF%.elf}.neorv32.bin"
HEX="${ELF%.elf}.neorv32.hex"
if ! "$CROSS-objcopy" -O binary "$ELF" "$BIN"; then
  echo "run-neorv32.sh: objcopy failed for $ELF" >&2
  exit 2
fi
od -An -v -tx4 -w4 "$BIN" | tr -d ' ' >"$HEX"

out="$(timeout --foreground -k 5 "$TIMEOUT" "$SIM" "+MEM=$HEX" "+MAX_CYCLES=$CYCLES" 2>&1)"
rc=$?
printf '%s\n' "$out"

# The testbench ends with $finish in every case, so the verdict comes from its output.
if [ "$rc" -eq 0 ]; then
  case $out in
  *"[TB] PASS after"*) rc=0 ;;
  *) rc=1 ;;
  esac
fi

if [ "$rc" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
  rm -f "$BIN" "$HEX"
else
  echo "run-neorv32.sh: memory image kept at $HEX (exit $rc)" >&2
fi
exit $rc
