#!/usr/bin/env bash
# Marin Radic mradic07@gmail.com
# SPDX-License-Identifier: Apache-2.0
# Install cve2 testbench (Verilator) for CI: cv32e20-dv.
# Usage: install-cve2.sh <install-dir>
# Cache key derives from sha256(this file)[:12]; bump versions/commits below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-cve2.sh <install-dir>}"
CVE2_DV_REPO="https://github.com/openhwgroup/cv32e20-dv.git"
CVE2_DV_COMMIT="69c16cbf84249744d5490b8fe48146ef532952a8"
VERILATOR_VERSION="v5.042"

mkdir -p "$INSTALL_DIR/bin"

# 1. Verilator from source
git clone --depth 1 --branch "$VERILATOR_VERSION" https://github.com/verilator/verilator.git "$INSTALL_DIR/verilator-src"
(
  cd "$INSTALL_DIR/verilator-src"
  autoconf
  ./configure --prefix="$INSTALL_DIR"
  make -j"$(nproc)"
  make install
)
rm -rf "$INSTALL_DIR/verilator-src"
export PATH="$INSTALL_DIR/bin:$PATH"

# 2. Clone cv32e20-dv at the pinned commit; fetch by SHA so the pin stays valid.
git init "$INSTALL_DIR/cv32e20-dv"
(
  cd "$INSTALL_DIR/cv32e20-dv"
  git remote add origin "$CVE2_DV_REPO"
  git fetch --depth 1 origin "$CVE2_DV_COMMIT"
  git checkout FETCH_HEAD
)

# 3. Verilate the rv32imc config (RTL hash pinned in sim/ExternalRepos.mk).
make -C "$INSTALL_DIR/cv32e20-dv/sim/core" \
  verilate \
  TEST=certification \
  -j"$(nproc)"

# 4. Install the cv32e20 per-test wrapper.
install -m 0755 "$INSTALL_DIR/cv32e20-dv/.github/scripts/run-cv32e20.sh" \
  "$INSTALL_DIR/bin/run-cv32e20.sh"
