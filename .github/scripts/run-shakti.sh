#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Run one ACT self-checking ELF on a Shakti core's Verilator testbench (E-class base-sim or
# C-class test_soc), shakti-<core>-sim beside this script, where install-shakti.sh puts it.
# Usage: run-shakti.sh --core eclass|cclass --elf <path>
# Env:   CROSS  toolchain prefix (default: riscv64-unknown-elf)
#
# The testbench loads main memory from code.mem and writes the UART output to app_log, both
# in its working directory, so each test runs in its own scratch directory. It always exits 0
# and has no cycle limit, so this runner prints app_log; run_tests.py applies the wall-clock
# timeout and checks the RVCP-SUMMARY line.
set -euo pipefail

CROSS="${CROSS:-riscv64-unknown-elf}"
[ "${1:-}" = --core ] && [ $# -ge 2 ] || {
  echo "Usage: run-shakti.sh --core eclass|cclass --elf <path-to-elf>" >&2
  exit 2
}
CORE="$2"
shift 2
[ "${1:-}" != --elf ] || shift
ELF="${1:?Usage: run-shakti.sh --core eclass|cclass --elf <path-to-elf>}"

# code.mem holds one memory word per line, the word at the base of RAM first. The word is as
# wide as the bus: 4 bytes on E-class (RV32), 8 on C-class (RV64).
case "$CORE" in
eclass) WORD=4 ;;
cclass) WORD=8 ;;
*)
  echo "run-shakti.sh: give --core eclass or --core cclass" >&2
  exit 2
  ;;
esac
SIM="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/shakti-$CORE-sim"
if [ ! -x "$SIM" ]; then
  echo "run-shakti.sh: no simulator at $SIM (build it with .github/scripts/install-shakti.sh)" >&2
  exit 2
fi

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
"$CROSS-objcopy" -O binary "$ELF" "$WORK/image.bin"
SIZE=$(stat -c %s "$WORK/image.bin")
truncate -s $(((SIZE + WORD - 1) / WORD * WORD)) "$WORK/image.bin"
od -An -v -tx$WORD -w$WORD "$WORK/image.bin" >"$WORK/code.mem"
cd "$WORK"
"$SIM" </dev/null
cat app_log
