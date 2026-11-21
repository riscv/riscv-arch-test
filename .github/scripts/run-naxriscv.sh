#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Run one ACT self-checking ELF on NaxRiscv's own Verilator simulator (src/test/cpp/naxriscv).
# The simulator loads the ELF, ends with SUCCESS when the nax_pass symbol commits and with
# FAILURE on a store to its failure address, a timeout, or 10000 cycles without a commit. It
# always exits 0 and records the verdict as a PASS or FAIL file in its output directory, so
# this runner turns that file into the exit status. Lock-step comparison with NaxRiscv's Spike
# is turned off: the tests check themselves against Sail.
# Usage: run-naxriscv.sh --elf <path>
# Env:   NAXRISCV_SIM     simulator executable (default: $HOME/repos/naxriscv-builds/bin/VNaxRiscv)
#        NAXRISCV_CYCLES  cycle limit (default: 50000000)
set -euo pipefail

SIM="${NAXRISCV_SIM:-$HOME/repos/naxriscv-builds/bin/VNaxRiscv}"
CYCLES="${NAXRISCV_CYCLES:-50000000}"
[ "${1:-}" != --elf ] || shift
ELF="${1:?Usage: run-naxriscv.sh --elf <path-to-elf>}"

if [ ! -x "$SIM" ]; then
  echo "run-naxriscv.sh: no simulator at $SIM (build it with .github/scripts/install-naxriscv.sh)" >&2
  exit 2
fi

OUT="$(mktemp -d)"
trap 'rm -rf "$OUT"' EXIT
# --timeout counts simulation time, two steps per cycle.
"$SIM" --load-elf "$ELF" --pass-symbol nax_pass --spike-disabled --no-stdin \
  --output-dir "$OUT" --timeout "$((CYCLES * 2))" </dev/null
[ -f "$OUT/PASS" ]
