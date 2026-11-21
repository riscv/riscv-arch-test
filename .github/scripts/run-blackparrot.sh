#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
#
# Run one ACT ELF on the verilated BlackParrot bp_tethered testbench (e_bp_unicore_cfg).
#
# Usage:  run-blackparrot.sh [--sim PATH] [--timeout SEC] [--keep DIR] [--quiet] --elf <path>
# Env:    BLACKPARROT_SIM  the testbench binary built by install-blackparrot.sh
#                          (bp_top/verilator/results/bp_tethered.e_bp_unicore_cfg/simsc)

set -uo pipefail

SIM="${BLACKPARROT_SIM:-}"
TIMEOUT=600
KEEP=""
QUIET=0
ELF=""

while [ $# -gt 0 ]; do
  case "$1" in
  --sim)
    SIM="$2"
    shift 2
    ;;
  --timeout)
    TIMEOUT="$2"
    shift 2
    ;;
  --keep)
    KEEP="$2"
    shift 2
    ;;
  --quiet)
    QUIET=1
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
  echo "run-blackparrot.sh: no ELF given" >&2
  exit 2
}
[ -f "$ELF" ] || {
  echo "run-blackparrot.sh: no such ELF: $ELF" >&2
  exit 2
}
[ -x "$SIM" ] || {
  echo "run-blackparrot.sh: no simulator at '$SIM' (set BLACKPARROT_SIM)" >&2
  exit 2
}

# The testbench writes its trace and stdout files to the working directory, so each test runs in
# its own scratch directory.
if [ -n "$KEEP" ]; then
  WORK="$KEEP"
  mkdir -p "$WORK"
else
  WORK="$(mktemp -d)"
  trap 'rm -rf "$WORK"' EXIT
fi

# The DRAM model loads a $readmemh image whose address 0 is the DRAM base (0x8000_0000), the
# same conversion the BlackParrot Makefiles use (mk/Makefile.collateral).
riscv64-unknown-elf-objcopy -O binary "$ELF" "$WORK/prog.bin" || exit 2
riscv64-unknown-elf-objcopy -I binary -O verilog "$WORK/prog.bin" "$WORK/prog.mem" || exit 2

# The cosimulation hook requires +elf_file even with cosimulation off.
ELF_ABS="$(cd "$(dirname "$ELF")" && pwd)/$(basename "$ELF")"
(cd "$WORK" && timeout --foreground -k 5 "$TIMEOUT" "$SIM" +init_mem=prog.mem +elf_file="$ELF_ABS" >sim.log 2>&1)
rc=$?

# The simulator log interleaves the console characters with its own messages, so the console
# output is printed again from stdout_global.txt, which holds only the characters written to the
# putchar register. --quiet prints only that. The per-instance "## work...instantiating" banners
# are dropped.
if [ "$QUIET" -eq 0 ]; then
  grep -v '^## work\.' "$WORK/sim.log"
  echo "--- console output (stdout_global.txt) ---"
fi
[ -f "$WORK/stdout_global.txt" ] && cat "$WORK/stdout_global.txt"
echo

# $finish exits 0 whether the test passed, failed, hit the cycle limit or the watchdog fired, so
# the verdict comes from the host device's message for a write to the finish register.
[ "$rc" -eq 0 ] || exit "$rc"
grep -q '^\[CORE FSH\] PASS' "$WORK/sim.log" || exit 1
exit 0
