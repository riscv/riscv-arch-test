#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Install the CVA6 + Ara Verilator model for CI.
# Usage: install-ara.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

# Resolved before any cd: the steps below run inside the Ara tree, where a path relative to
# $0 no longer refers to this script's directory.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INSTALL_DIR="${1:?Usage: install-ara.sh <install-dir>}"
ARA_REPO="https://github.com/pulp-platform/ara.git"
ARA_COMMIT="34bd3bc152421b4601a7bf3d6e8e91ffb545c99e"

# Ara pins its own Verilator (5.047-devel) as a submodule and builds it with `make
# verilator`. That version is not optional: hierarchical sub-verilation is what makes
# this model usable at all (~15,000 cycles/s versus ~100 cycles/s for a flat build),
# and Verilator releases before 5.046 drop the +incdir+/+define+ lines from Bender's
# flist when --hierarchical is used, so the design does not even elaborate.
mkdir -p "$INSTALL_DIR"

git init "$INSTALL_DIR/ara"
(
  cd "$INSTALL_DIR/ara"
  git remote add origin "$ARA_REPO"
  git fetch --depth 1 origin "$ARA_COMMIT"
  git checkout FETCH_HEAD
  git submodule update --init --recursive toolchain/verilator
)

(
  cd "$INSTALL_DIR/ara"
  # 1. Ara's pinned Verilator (~4 min on 32 cores).
  make verilator
  export PATH="$INSTALL_DIR/ara/install/verilator/bin:$PATH"

  # 2. Bender downloads a prebuilt binary; no Rust toolchain is needed.
  make -C hardware checkout
  make -C hardware apply-patches

  # 3. Widen the testbench's ELF loader window, then verilate.
  "$SCRIPT_DIR/setup-ara.sh" "$INSTALL_DIR" --patch-only

  # nr_lanes=4 with VLEN=512. VLEN is an independent -G parameter; 512 is roughly 15x
  # cheaper in wall clock than Ara's 4096 default and about 8x smaller in signature
  # memory, for the same architectural coverage.
  make -C hardware verilate nr_lanes=4 vlen=512 buildpath="$INSTALL_DIR/build"
)

mkdir -p "$INSTALL_DIR/bin"
install -m 0755 "$SCRIPT_DIR/run-ara.sh" "$INSTALL_DIR/bin/run-ara.sh"
