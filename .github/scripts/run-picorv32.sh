#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Run one ACT self-checking ELF on a verilated PicoRV32.
#
# ACT4 tests self-check and report by printing to the console, so this runner does
# not produce or compare a signature: it loads the ELF, runs the testbench, and
# lets the RVCP-SUMMARY line reach stdout where run_tests.py parses it.
#
# Usage:  run-picorv32.sh [--snapshot DIR] [--timeout SEC] [--max-cycles N] [--keep] --elf <path>
#   run_tests.py appends the ELF path as the final argument.
# Env:    PICORV32_SNAPSHOT  directory holding obj_dir/Vpicorv32_wrapper
#                            (default: ~/repos/picorv32-builds/act)
#         CROSS              toolchain prefix (default: riscv64-unknown-elf)
#         PICORV32_TEST_BASE load address of the image; must equal TEST_BASE in
#                            link.ld and PROGADDR_RESET in install-picorv32.sh

set -uo pipefail

SNAPSHOT="${PICORV32_SNAPSHOT:-$HOME/repos/picorv32-builds/act}"
CROSS="${CROSS:-riscv64-unknown-elf}"
TEST_BASE="${PICORV32_TEST_BASE:-0x4000}"
TIMEOUT=280
MAX_CYCLES=20000000
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
  --max-cycles)
    MAX_CYCLES="$2"
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
  echo "run-picorv32.sh: no ELF given" >&2
  exit 2
}
[ -f "$ELF" ] || {
  echo "run-picorv32.sh: no such ELF: $ELF" >&2
  exit 2
}
SIM="$SNAPSHOT/obj_dir/Vpicorv32_wrapper"
[ -x "$SIM" ] || {
  echo "run-picorv32.sh: no simulator at $SIM (build it with install-picorv32.sh)" >&2
  exit 2
}

WORK="${ELF%.elf}.picorun"
rm -rf "$WORK"
mkdir -p "$WORK" || exit 2

# picorv32's testbench loads its image with $readmemh into a word array that
# starts at address 0, so the hex file is one 32-bit word per line covering
# address 0 upward. `objcopy -O verilog` is the wrong format here: it emits byte
# records with @ address directives. Use a flat binary and front-pad it to
# TEST_BASE, which is what firmware/makehex.py does for picorv32's own firmware.
"$CROSS-objcopy" -O binary "$ELF" "$WORK/test.bin" || exit 2
python3 - "$WORK/test.bin" "$WORK/test.hex" "$TEST_BASE" <<'PYEOF' || exit 2
import struct
import sys

src, dst, base = sys.argv[1], sys.argv[2], int(sys.argv[3], 0)
data = open(src, "rb").read()
data += b"\x00" * (-len(data) % 4)
words = struct.unpack("<%dI" % (len(data) // 4), data)
with open(dst, "w") as f:
    f.write("0\n" * (base // 4))
    f.write("".join("%08x\n" % w for w in words))
PYEOF

# The testbench ends the simulation with $finish on every path (install-picorv32.sh
# rewrites its one $stop), so the custom main() in picorv32-act-main.cc always gets
# to inspect trap/tests_passed and pick the exit code.
out="$(timeout --foreground -k 5 "$TIMEOUT" "$SIM" \
  "+firmware=$WORK/test.hex" "+max-cycles=$MAX_CYCLES" 2>&1)"
rc=$?
printf '%s\n' "$out"

# Belt and braces: the exit code already distinguishes pass, fail, hang and
# out-of-bounds, but a test that printed TEST FAILED and then somehow reached the
# pass token must not be reported as a pass.
if [ "$rc" -eq 0 ] && printf '%s' "$out" | grep -q 'RVCP-SUMMARY: TEST FAILED'; then
  rc=1
fi

if [ "$rc" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
  rm -rf "$WORK"
else
  echo "run-picorv32.sh: artifacts kept in $WORK (exit $rc)" >&2
fi
exit $rc
