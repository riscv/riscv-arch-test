#!/usr/bin/env bash
# Run one ACT self-checking ELF on a verilated VeeR core.
#
# ACT4 tests self-check and report by printing to the console, so this runner does not
# produce or compare a signature: it loads the ELF, runs the testbench, and lets the
# RVCP-SUMMARY line reach stdout where run_tests.py parses it.
#
# Usage:  run-veer.sh [--snapshot DIR] [--timeout SEC] [--keep] --elf <path>
#   run_tests.py appends the ELF path as the final argument.
# Env:    VEER_SNAPSHOT  directory holding obj_dir/Vtb_top   (default: ~/repos/veer-builds/eh1)
#         CROSS          toolchain prefix                    (default: riscv64-unknown-elf)
set -uo pipefail

SNAPSHOT="${VEER_SNAPSHOT:-$HOME/repos/veer-builds/eh1}"
CROSS="${CROSS:-riscv64-unknown-elf}"
TIMEOUT=280
KEEP=0
ELF=""

while [ $# -gt 0 ]; do
  case "$1" in
    --snapshot) SNAPSHOT="$2"; shift 2 ;;
    --timeout)  TIMEOUT="$2";  shift 2 ;;
    --keep)     KEEP=1;        shift ;;
    --elf)      shift ;;                 # the ELF is the trailing argument
    *)          ELF="$1";      shift ;;
  esac
done

[ -n "$ELF" ]      || { echo "run-veer.sh: no ELF given" >&2; exit 2; }
[ -f "$ELF" ]      || { echo "run-veer.sh: no such ELF: $ELF" >&2; exit 2; }
SIM="$SNAPSHOT/obj_dir/Vtb_top"
[ -x "$SIM" ]      || { echo "run-veer.sh: no simulator at $SIM (build it with tools/Makefile verilator-build)" >&2; exit 2; }

# The VeeR testbench hard-codes program.hex / console.log / exec.log relative to the
# current directory, so every test needs its own directory to run in parallel safely.
WORK="${ELF%.elf}.veerrun"
rm -rf "$WORK"; mkdir -p "$WORK" || exit 2

"$CROSS-objcopy" -O verilog "$ELF" "$WORK/test.hex" || exit 2

# VeeR EH1's testbench hard-codes the reset vector to 0 (tb_top.sv: "reset_vector = 32'h0;"),
# but ACT cannot link its image at address 0, so the tests are linked at TEST_BASE=0x1000
# and we prepend a two-instruction boot stub at 0 that jumps there:
#   lui t0, 0x1 ; jr t0
printf '@00000000\n85 62 82 82\n' > "$WORK/program.hex"
cat "$WORK/test.hex" >> "$WORK/program.hex"

# The testbench's instruction-trace writer is unguarded and emits two lines plus a full
# disassembly per retired instruction. Discard it; console.log is what we need.
ln -sf /dev/null "$WORK/exec.log"
ln -sf /dev/null "$WORK/trace_port.csv"

out="$( cd "$WORK" && timeout --foreground -k 5 "$TIMEOUT" "$SIM" 2>&1 )"
rc=$?
printf '%s\n' "$out"

# VeeR EH1's testbench ends a failing test with $finish, not $fatal, so the process exit
# code is 0 even on failure (EL2 uses $fatal). Derive the verdict from the console instead.
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q 'TEST_FAILED'; then
  rc=1
fi

if [ "$rc" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
  rm -rf "$WORK"
else
  echo "run-veer.sh: artifacts kept in $WORK (exit $rc)" >&2
fi
exit $rc
