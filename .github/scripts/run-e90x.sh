#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Run one ACT self-checking ELF on a verilated XuanTie OpenE902 or OpenE906 smart_run SoC
# testbench. The testbench always exits 0 and writes its verdict to run_case.report, so this
# runner turns that file into the exit status. run_tests.py applies the wall-clock timeout and
# checks the exit status and the RVCP-SUMMARY line.
# Usage: run-e90x.sh --elf <path>
# Env:   E90X_SIM  testbench executable (default: Vtb next to this script)
#        CROSS     toolchain prefix (default: riscv64-unknown-elf)
set -euo pipefail

SIM="$(readlink -f "${E90X_SIM:-$(dirname "${BASH_SOURCE[0]}")/Vtb}")"
CROSS="${CROSS:-riscv64-unknown-elf}"
[ "${1:-}" != --elf ] || shift
ELF="${1:?Usage: run-e90x.sh --elf <path-to-elf>}"

if [ ! -x "$SIM" ]; then
  echo "run-e90x.sh: no simulator at $SIM (build it with the core's .github/scripts/install-e90*.sh)" >&2
  exit 2
fi

# The testbench reads mem.pat from, and writes run_case.report to, its working directory.
# mem.pat holds one 32-bit hex word per line with the lowest address in the most significant
# byte, starting at address 0. Pad the image to whole words: od prints a short last line,
# which $readmemh would read as a right-justified word and so load into the wrong bytes.
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
"$CROSS-objcopy" -O binary --gap-fill 0 "$ELF" "$WORK/image.bin"
truncate -s %4 "$WORK/image.bin"
od -An -tx1 -v -w4 "$WORK/image.bin" | tr -d ' ' | grep -v '^$' >"$WORK/mem.pat"
cd "$WORK"
"$SIM" </dev/null
grep -qx 'TEST PASS' run_case.report
