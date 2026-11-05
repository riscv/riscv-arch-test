#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Run one ACT self-checking ELF on an OpenHW CVA6 Verilator testharness.
# Usage: run-cva6.sh --target <cv32a60x|cv32a65x|...> [--trace FILE] [--timeout SEC] [--keep] --elf <path>
# Env:   CVA6_TARGET   default target if --target is not given
#        CVA6_SNAPSHOT install-cva6.sh install directory (default: ~/repos/cva6-builds)
#        CROSS         toolchain prefix (default: riscv64-unknown-elf)
#
# --trace FILE writes a spike-dasm instruction trace to FILE and an FST waveform next to it.
set -uo pipefail

SELF="run-cva6.sh"
TARGET="${CVA6_TARGET:-}"
SNAPSHOT="${CVA6_SNAPSHOT:-$HOME/repos/cva6-builds}"
CROSS="${CROSS:-riscv64-unknown-elf}"
TIMEOUT=1800
KEEP=0
TRACE=""
ELF=""

while [ $# -gt 0 ]; do
  case "$1" in
  --target)
    TARGET="$2"
    shift 2
    ;;
  --trace)
    TRACE="$2"
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

[ -n "$TARGET" ] || {
  echo "$SELF: no target given (use --target <name> or set CVA6_TARGET)" >&2
  exit 2
}

# ISA string for spike-dasm, chosen by the target's XLEN.
case "$TARGET" in
cv32*)
  SPIKE_ISA="rv32imc_zicsr_zifencei_zcb_zba_zbb_zbc_zbs"
  ;;
cv64*)
  SPIKE_ISA="rv64imafdc_zicsr_zifencei_zba_zbb_zbc_zbs"
  ;;
*)
  echo "$SELF: unknown target '$TARGET' (expected cv32* or cv64*)" >&2
  exit 2
  ;;
esac

[ -n "$ELF" ] || {
  echo "$SELF: no ELF given" >&2
  exit 2
}
[ -f "$ELF" ] || {
  echo "$SELF: no such ELF: $ELF" >&2
  exit 2
}

SIM="$SNAPSHOT/cva6/work-ver-$TARGET/Variane_testharness"
[ -x "$SIM" ] || {
  echo "$SELF: no simulator for $TARGET at $SIM (build it with .github/scripts/install-cva6.sh)" >&2
  exit 2
}

ELF_ABS="$(readlink -f "$ELF")"
TEST_FILE="$(basename "$ELF" .elf).S"

# The testbench polls tohost for the halt code, so it needs the symbol address.
TOHOST="$("$CROSS-nm" -B "$ELF_ABS" | awk '$3 == "tohost" { print $1; exit }')"
[ -n "$TOHOST" ] || {
  echo "$SELF: symbol tohost not found in $ELF" >&2
  exit 2
}

# The testbench writes trace_rvfi_hart_00.dasm into the current directory, so every test
# needs its own directory to run in parallel.
WORK="${ELF%.elf}.cva6run"
rm -rf "$WORK"
mkdir -p "$WORK" || exit 2

args=("$ELF_ABS" "+tohost_addr=$TOHOST" "+elf_file=$ELF_ABS")
FST=""
if [ -n "$TRACE" ]; then
  mkdir -p "$(dirname "$TRACE")"
  TRACE="$(readlink -f "$TRACE")"
  FST="${TRACE%.trace.log}.fst"
  args=(-f "$FST" "${args[@]}")
fi

simout="$(cd "$WORK" && timeout --foreground -k 5 "$TIMEOUT" "$SIM" "${args[@]}" 2>&1)"
simrc=$?
printf '%s\n' "$simout"

if [ -n "$TRACE" ]; then
  if [ -f "$WORK/trace_rvfi_hart_00.dasm" ]; then
    "$SNAPSHOT/spike/bin/spike-dasm" --isa="$SPIKE_ISA" <"$WORK/trace_rvfi_hart_00.dasm" >"$TRACE"
  else
    echo "$SELF: no trace_rvfi_hart_00.dasm, so no instruction trace in $TRACE" >&2
  fi
fi

# The testbench prints *** SUCCESS *** or *** FAILED *** when the test writes tohost.
rc=0
if grep -q '\*\*\* SUCCESS \*\*\*' <<<"$simout"; then
  printf 'RVCP-SUMMARY: TEST PASSED - Test File "%s"\n' "$TEST_FILE"
elif grep -q '\*\*\* FAILED \*\*\*' <<<"$simout"; then
  printf 'RVCP-SUMMARY: TEST FAILED - Test File "%s"\n' "$TEST_FILE"
  rc=1
else
  echo "$SELF: no SUCCESS/FAILED marker (simulator exit $simrc, timeout is ${TIMEOUT}s)" >&2
  rc=1
fi

if [ "$rc" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
  rm -rf "$WORK"
else
  echo "$SELF: artifacts kept in $WORK (exit $rc)" >&2
fi
exit $rc
