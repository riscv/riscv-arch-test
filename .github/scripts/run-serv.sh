#!/usr/bin/env bash
# Run one ACT self-checking ELF on a verilated SERV core in the servant reference SoC.
#
# ACT4 tests self-check and report by printing to the console, so this runner does not
# produce or compare a signature.  It converts the ELF to the word-per-line hex image that
# servant_sim's +firmware loader expects, runs the testbench, and prints whatever the test
# wrote to servile_mux's sim_sig_adr hook, which this port uses as the console.
#
# The stock bench/servant_tb.cpp ends in an unconditional exit(0), so a timeout, a hang and
# a failing test all look like success to the shell.  The verdict therefore comes from the
# console text: a run that does not reach the sim_halt_adr hook (which prints
# "Test complete") fails, and so does one whose RVCP-SUMMARY line says TEST FAILED.
#
# Usage:  run-serv.sh [--snapshot DIR] [--timeout SEC] [--sim-timeout NS] [--keep] --elf <path>
#   run_tests.py appends the ELF path as the final argument.
# Env:    SERV_SNAPSHOT  directory holding obj/Vservant_sim (default: ~/repos/serv-builds/act)
#         CROSS          toolchain prefix (default: riscv64-unknown-elf)
set -uo pipefail

SNAPSHOT="${SERV_SNAPSHOT:-$HOME/repos/serv-builds/act}"
CROSS="${CROSS:-riscv64-unknown-elf}"
# Wall-clock ceiling.  SERV needs 32+ cycles per instruction, so an ACT test that takes a
# reference model a second takes SERV minutes.
TIMEOUT=3600
# Simulated-time ceiling in ns, passed to the testbench as +timeout.  servant_tb advances
# 31.25 ns per half cycle, so 16 ns of simulated time is one clock cycle:
# 4e9 ns is about 250 M cycles.
SIM_TIMEOUT=4000000000
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

# servant_sim's +firmware loader is a bare $readmemh into the RAM array, so the image must be
# one 32-bit little-endian word per line starting at address 0 with no address records.  The
# tests link at 0 (see link.ld), so a flat objcopy image is already in the right place.
"$CROSS-objcopy" -O binary "$ELF" "$WORK/test.bin" || exit 2
# $readmemh fills the array in order, so the image must be a whole number of words.
truncate -s "$(((($(stat -c %s "$WORK/test.bin") + 3) / 4) * 4))" "$WORK/test.bin" || exit 2
od -An -tx4 -v -w4 "$WORK/test.bin" | tr -d ' ' >"$WORK/test.hex" || exit 2

out="$(cd "$WORK" && timeout --foreground -k 5 "$TIMEOUT" "$SIM" \
  "+firmware=test.hex" "+signature=console.txt" "+timeout=$SIM_TIMEOUT" 2>&1)"
rc=$?
# The console is written through $fwrite, so it lands in the file rather than on stdout.
console="$(cat "$WORK/console.txt" 2>/dev/null)"
printf '%s\n' "$console"
printf '%s\n' "$out"

# Matched with shell globs rather than `grep -q`: under `set -o pipefail` a `grep -q` that
# exits on its first match can SIGPIPE the writer and turn the whole pipeline's status into
# 141, which reads as "no match" and silently inverts the verdict.
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
