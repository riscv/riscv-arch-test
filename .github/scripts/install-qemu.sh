#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Install QEMU from source
# Usage: install-qemu.sh <install-dir>
# Update QEMU_VERSION to rebuild with a newer version (cache key is derived from this script's hash).

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-qemu.sh <install-dir>}"
QEMU_VERSION="11.0.0" # Latest version as of April 5, 2026

curl --location "https://download.qemu.org/qemu-${QEMU_VERSION}.tar.xz" | tar xvJ
cd "qemu-${QEMU_VERSION}"
./configure --prefix="$INSTALL_DIR" --target-list=riscv32-softmmu,riscv64-softmmu
make -j"$(nproc)"
make install
