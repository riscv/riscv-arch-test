#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Jordan Carlin jcarlin@hmc.edu April 2026
# Install Whisper RISC-V ISA Simulator from source
# Usage: install-whisper.sh <install-dir>
# Update WHISPER_COMMIT to rebuild with a newer version (cache key is derived from this script's hash).

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-whisper.sh <install-dir>}"
WHISPER_COMMIT="34db6da6946ffe6dfb7d2977160046c875d4c8bf" # Latest as of April 6, 2026

git clone https://github.com/tenstorrent/whisper.git
cd whisper
git checkout "$WHISPER_COMMIT"
make -j"$(nproc)"
mkdir -p "$INSTALL_DIR/bin"
cp build-Linux/whisper "$INSTALL_DIR/bin/"
