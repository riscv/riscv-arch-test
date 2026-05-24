#!/usr/bin/env bash
# Marin Radic mradic07@gmail.com
# SPDX-License-Identifier: Apache-2.0
# Install cv32e40p-dv testbench (Verilator) for CI
# Usage: install-cve4.sh <install-dir>
# Cache key derives from sha256(this file)[:12]; bump versions/commits below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-cve4.sh <install-dir>}"
CVE4_DV_REPO="https://github.com/openhwgroup/cv32e40p-dv-review.git"
CVE4_DV_COMMIT="a1c4ec501e82f23987d1d74625b70a6cd1dfc2e1"
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

# 2. Clone the cv32e40p-dv testbench at the pinned commit (shallow).
# Fetch by SHA (not branch tip) so the pin remains valid as upstream advances.
git init "$INSTALL_DIR/cv32e40p-dv"
(
  cd "$INSTALL_DIR/cv32e40p-dv"
  git remote add origin "$CVE4_DV_REPO"
  git fetch --depth 1 origin "$CVE4_DV_COMMIT"
  git checkout FETCH_HEAD
)

# 3. Build a Verilator binary per cv32e40p config (TEST = certification_<config>).
make -C "$INSTALL_DIR/cv32e40p-dv/sim/core" \
    verilate \
    CV_CORE_CONFIG=rv32imcf \
    TEST=certification_rv32imcf \
    -j"$(nproc)"

make -C "$INSTALL_DIR/cv32e40p-dv/sim/core" \
    verilate \
    CV_CORE_CONFIG=rv32imc \
    TEST=certification_rv32imc \
    -j"$(nproc)"

# v1.0.0_rv32imc also clones the pinned v1.0.0 RTL (Makefile handles it).
make -C "$INSTALL_DIR/cv32e40p-dv/sim/core" \
    verilate \
    CV_CORE_CONFIG=v1.0.0_rv32imc \
    TEST=certification_v1.0.0_rv32imc \
    -j"$(nproc)"

# 4. Drop the per-test wrapper into $INSTALL_DIR/bin for easy invocation from CI
install -m 0755 "$INSTALL_DIR/cv32e40p-dv/.github/scripts/run-cve4.sh" \
                "$INSTALL_DIR/bin/run-cve4.sh"
