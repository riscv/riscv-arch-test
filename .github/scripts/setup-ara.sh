#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Setup environment for CVA6 + Ara after install / cache restore.
# Usage: setup-ara.sh <install-dir> [--patch-only]
#   --patch-only applies the testbench source patch and exits; install-ara.sh calls it
#   that way before verilating, and CI calls it without the flag after a cache restore.

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-ara.sh <install-dir> [--patch-only]}"
PATCH_ONLY="${2:-}"

TB_CPP="$INSTALL_DIR/ara/hardware/tb/verilator/ara_tb.cpp"

# Widen the testbench ELF loader window from 1 MiB to 16 MiB, the size of the L2 and of
# RAM_LENGTH in link.ld. ACT's vector ELFs exceed 1 MiB.
#   https://github.com/pulp-platform/ara/blob/34bd3bc152421b4601a7bf3d6e8e91ffb545c99e/hardware/tb/verilator/lowrisc_dv_verilator_memutil_dpi/cpp/dpi_memutil.cc#L257
if [ -f "$TB_CPP" ]; then
  sed -i 's/{\.base=0x80000000, \.size=0x00100000}/{.base=0x80000000, .size=0x01000000}/' "$TB_CPP"
  grep -q '\.size=0x01000000' "$TB_CPP" || {
    echo "setup-ara.sh: failed to widen the ELF loader window in $TB_CPP" >&2
    exit 1
  }
fi

if [ "$PATCH_ONLY" = "--patch-only" ]; then
  exit 0
fi

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "ARA_SNAPSHOT=$INSTALL_DIR/build" >>"$GITHUB_ENV"
