#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Jordan Carlin jcarlin@hmc.edu April 2026
# Install Spike RISC-V ISA Simulator from source
# Usage: install-spike.sh <install-dir>
# Update SPIKE_COMMIT to rebuild with a newer version (cache key is derived from this script's hash).

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-spike.sh <install-dir>}"
SPIKE_COMMIT="56fd48e786604770fac73a8873c80525c1f00eed"

git clone https://github.com/riscv/riscv-isa-sim.git
cd riscv-isa-sim
git checkout "$SPIKE_COMMIT"
mkdir build && cd build
../configure --prefix="$INSTALL_DIR"
make -j"$(nproc)"
make install
