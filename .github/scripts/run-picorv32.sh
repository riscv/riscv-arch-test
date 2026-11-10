#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
#
# Run one ACT ELF on a verilated PicoRV32.
#
# Usage:  run-picorv32.sh [--snapshot DIR] [--timeout SEC] [--max-cycles N] [--keep] --elf <path>
# Env:    PICORV32_SNAPSHOT  install directory of install-picorv32.sh
#         CROSS              toolchain prefix (default: riscv64-unknown-elf)

set -uo pipefail

SNAPSHOT="${PICORV32_SNAPSHOT:-}"
CROSS="${CROSS:-riscv64-unknown-elf}"
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

# The testbench $readmemh's one 32-bit word per line from address 0, the format
# of picorv32's firmware/makehex.py.
"$CROSS-objcopy" -O binary "$ELF" "$WORK/test.bin" || exit 2
python3 - "$WORK/test.bin" "$WORK/test.hex" <<'PYEOF' || exit 2
import struct
import sys

src, dst = sys.argv[1], sys.argv[2]
data = open(src, "rb").read()
data += b"\x00" * (-len(data) % 4)
words = struct.unpack("<%dI" % (len(data) // 4), data)
with open(dst, "w") as f:
    f.write("".join("%08x\n" % w for w in words))
PYEOF

timeout --foreground -k 5 "$TIMEOUT" "$SIM" "+firmware=$WORK/test.hex" "+max-cycles=$MAX_CYCLES" 2>&1
rc=$?

if [ "$rc" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
  rm -rf "$WORK"
else
  echo "run-picorv32.sh: artifacts kept in $WORK (exit $rc)" >&2
fi
exit $rc
