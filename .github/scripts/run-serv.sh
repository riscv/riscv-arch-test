#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Run one ACT self-checking ELF on SERV in the servant SoC under Verilator.
# Usage: run-serv.sh [--snapshot DIR] [--timeout SEC] [--sim-timeout TICKS] [--keep] --elf <path>
# Env:   SERV_SNAPSHOT  directory holding obj/Vservant_sim (default: ~/repos/serv-builds/act)
#        CROSS          toolchain prefix (default: riscv64-unknown-elf)
set -uo pipefail

SNAPSHOT="${SERV_SNAPSHOT:-$HOME/repos/serv-builds/act}"
CROSS="${CROSS:-riscv64-unknown-elf}"
# Wall-clock limit in seconds.  SERV takes 32+ cycles per instruction.
TIMEOUT=3600
# Simulated-time limit, passed as +timeout.  servant_tb reads it with atoi, so it must fit in
# an int; at 62 time units per clock cycle this is about 32 M cycles.
SIM_TIMEOUT=2000000000
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
  --sim-timeout)
    SIM_TIMEOUT="$2"
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
  echo "run-serv.sh: no ELF given" >&2
  exit 2
}
[ -f "$ELF" ] || {
  echo "run-serv.sh: no such ELF: $ELF" >&2
  exit 2
}
SIM="$SNAPSHOT/obj/Vservant_sim"
[ -x "$SIM" ] || {
  echo "run-serv.sh: no simulator at $SIM (see .github/scripts/install-serv.sh)" >&2
  exit 2
}

WORK="${ELF%.elf}.servrun"
rm -rf "$WORK"
mkdir -p "$WORK" || exit 2

# +firmware is a $readmemh into the RAM array: one 32-bit word per line, starting at address 0.
"$CROSS-objcopy" -O binary "$ELF" "$WORK/test.bin" || exit 2
# Pad the image to a whole number of words.
truncate -s "$(((($(stat -c %s "$WORK/test.bin") + 3) / 4) * 4))" "$WORK/test.bin" || exit 2
od -An -tx4 -v -w4 "$WORK/test.bin" | tr -d ' ' >"$WORK/test.hex" || exit 2

out="$(cd "$WORK" && timeout --foreground -k 5 "$TIMEOUT" "$SIM" \
  "+firmware=test.hex" "+signature=console.txt" "+timeout=$SIM_TIMEOUT" 2>&1)"
rc=$?
# servile_mux appends each byte stored to 0x8000_0000 to the +signature= file, which the tests
# use as their console.
console="$(cat "$WORK/console.txt" 2>/dev/null)"
printf '%s\n' "$console"
printf '%s\n' "$out"

# bench/servant_tb.cpp always exits 0, so the verdict comes from the output: the run must reach
# the halt hook ("Test complete") and the console must not report TEST FAILED.
if [ "$rc" -eq 0 ]; then
  case "$out" in
  *"Timeout: Exiting at time"*)
    echo "run-serv.sh: simulated-time limit reached without halting" >&2
    rc=1
    ;;
  *"Test complete"*) ;;
  *)
    echo "run-serv.sh: simulation ended without reaching the halt hook" >&2
    rc=1
    ;;
  esac
fi
if [ "$rc" -eq 0 ]; then
  case "$console" in
  *"TEST FAILED"*) rc=1 ;;
  *"RVCP-SUMMARY"*) ;;
  *)
    echo "run-serv.sh: no RVCP-SUMMARY line on the console" >&2
    rc=1
    ;;
  esac
elif [ "$rc" -ge 124 ]; then
  echo "run-serv.sh: wall-clock timeout after ${TIMEOUT}s" >&2
fi

if [ "$rc" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
  rm -rf "$WORK"
else
  echo "run-serv.sh: artifacts kept in $WORK (exit $rc)" >&2
fi
exit $rc
