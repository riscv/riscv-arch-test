#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Jordan Carlin jcarlin@hmc.edu April 2026
# Install Spike RISC-V ISA Simulator from source
# Usage: install-spike.sh <install-dir>
# Update SPIKE_COMMIT to rebuild with a newer version (cache key is derived from this script's hash).

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-spike.sh <install-dir>}"
SPIKE_COMMIT="3e43e67632cdc386b84e5bea1cf613b062b07bf6"

git clone https://github.com/riscv/riscv-isa-sim.git
cd riscv-isa-sim
git checkout "$SPIKE_COMMIT"
mkdir build && cd build
../configure --prefix="$INSTALL_DIR"
make -j"$(nproc)"
make install
