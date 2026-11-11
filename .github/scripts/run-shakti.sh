#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Run one ACT self-checking ELF on a Shakti core's Verilator testbench (E-class base-sim or
# C-class test_soc).
# Usage: run-shakti.sh --core eclass|cclass [--sim PATH] [--timeout SEC] [--keep] --elf <path>
# The simulator defaults to shakti-<core>-sim beside this script, where install-shakti.sh puts
# it.
# Env:   CROSS  toolchain prefix (default: riscv64-unknown-elf)
#
# The testbench loads main memory from code.mem and writes the UART output to app_log, both
# in its working directory, so each test runs in its own scratch directory. Its main() always
# exits 0 and has no cycle limit, so the verdict comes from app_log, and a test that never
# ends is stopped by the timeout.
set -uo pipefail

CROSS="${CROSS:-riscv64-unknown-elf}"
SIM=""
CORE=""
TIMEOUT=240
KEEP=0
ELF=""

while [ $# -gt 0 ]; do
  case "$1" in
  --core)
    CORE="$2"
    shift 2
    ;;
  --sim)
    SIM="$2"
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
  echo "run-shakti.sh: no ELF given" >&2
  exit 2
fi
if [ ! -f "$ELF" ]; then
  echo "run-shakti.sh: no such ELF: $ELF" >&2
  exit 2
fi
if [ -z "$SIM" ]; then
  case "$CORE" in
  eclass | cclass) SIM="$(dirname "$0")/shakti-$CORE-sim" ;;
  *)
    echo "run-shakti.sh: give --core eclass or --core cclass, or --sim" >&2
    exit 2
    ;;
  esac
fi
if [ ! -x "$SIM" ]; then
  echo "run-shakti.sh: no simulator at '$SIM' (build it with .github/scripts/install-shakti.sh)" >&2
  exit 2
fi
SIM="$(cd "$(dirname "$SIM")" && pwd)/$(basename "$SIM")"

WORK="$(mktemp -d "${TMPDIR:-/tmp}/shakti.XXXXXX")"

# code.mem holds one memory word per line, the word at the base of RAM first. The word is as
# wide as the bus: 4 bytes on RV32, 8 on RV64, which the ELF class gives.
case "$(od -An -j4 -N1 -tu1 "$ELF" | tr -d ' ')" in
1) WORD=4 ;;
2) WORD=8 ;;
*)
  echo "run-shakti.sh: $ELF is not an ELF file" >&2
  exit 2
  ;;
esac
if ! "$CROSS-objcopy" -O binary "$ELF" "$WORK/image.bin"; then
  echo "run-shakti.sh: objcopy failed for $ELF" >&2
  exit 2
fi
SIZE=$(stat -c %s "$WORK/image.bin")
truncate -s $(((SIZE + WORD - 1) / WORD * WORD)) "$WORK/image.bin"
od -An -v -tx$WORD -w$WORD "$WORK/image.bin" >"$WORK/code.mem"

(cd "$WORK" && timeout --foreground -k 5 "$TIMEOUT" "$SIM" >sim.log 2>&1)
rc=$?

log=""
[ -f "$WORK/app_log" ] && log="$(cat "$WORK/app_log")"
printf '%s\n' "$log"

if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
  echo "run-shakti.sh: timed out after ${TIMEOUT}s" >&2
  status=1
elif [ "$rc" -ne 0 ]; then
  echo "run-shakti.sh: simulator exited with status $rc" >&2
  tail -n 20 "$WORK/sim.log" >&2
  status=1
else
  case $log in
  *"RVCP-SUMMARY: TEST PASSED"*) status=0 ;;
  *) status=1 ;;
  esac
fi

if [ "$status" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
  rm -rf "$WORK"
else
  echo "run-shakti.sh: scratch directory kept at $WORK" >&2
fi
exit $status
