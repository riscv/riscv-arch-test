#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Build the Chipyard Verilator simulator for Rocket + Saturn + H (ACTRocketSaturnHConfig) for CI.
# Usage: install-rocket.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.
#
# Chipyard's own build-setup.sh installs a conda environment and a RISC-V toolchain; neither is
# needed to build a Verilator simulator, so this script installs only what the build uses:
# Verilator, a JDK for sbt, CIRCT firtool, espresso, and Spike's libfesvr/libriscv.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${1:?Usage: install-rocket.sh <install-dir>}"
mkdir -p "$INSTALL_DIR/bin"
INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd)"
JOBS="${JOBS:-$(nproc)}"

CHIPYARD_REPO="https://github.com/ucb-bar/chipyard.git"
CHIPYARD_COMMIT="0acc1e1de2d3284bcd4d876956932a013ffe1949" # 1.14.0
VERILATOR_VERSION="v5.036"
FIRTOOL_VERSION="1.75.0" # conda-reqs/circt.json at the pinned Chipyard commit
JDK_URL="https://api.adoptium.net/v3/binary/version/jdk-17.0.16%2B8/linux/x64/jdk/hotspot/normal/eclipse"
CONFIG="ACTRocketSaturnHConfig"

TOOLS="$INSTALL_DIR/tools"
mkdir -p "$TOOLS"

# 1. Verilator
git clone --depth 1 --branch "$VERILATOR_VERSION" https://github.com/verilator/verilator.git "$TOOLS/verilator-src"
(
  cd "$TOOLS/verilator-src"
  autoconf
  ./configure --prefix="$TOOLS/verilator"
  make -j"$JOBS"
  make install
)
rm -rf "$TOOLS/verilator-src"

# 2. JDK 17 (sbt) and CIRCT firtool
mkdir -p "$TOOLS/jdk"
curl -fsSL "$JDK_URL" | tar -xz -C "$TOOLS/jdk" --strip-components=1
mkdir -p "$TOOLS/firtool"
curl -fsSL "https://github.com/llvm/circt/releases/download/firtool-$FIRTOOL_VERSION/firrtl-bin-linux-x64.tar.gz" |
  tar -xz -C "$TOOLS/firtool" --strip-components=1
export PATH="$TOOLS/verilator/bin:$TOOLS/jdk/bin:$TOOLS/firtool/bin:$TOOLS/espresso/bin:$PATH"

# 3. Chipyard at the pinned commit, with the submodules a Rocket + Saturn build needs
git init "$INSTALL_DIR/chipyard"
cd "$INSTALL_DIR/chipyard"
git remote add origin "$CHIPYARD_REPO"
git fetch --depth 1 origin "$CHIPYARD_COMMIT"
git checkout FETCH_HEAD
./scripts/init-submodules-no-riscv-tools.sh --saturn
git submodule update --init --depth 1 toolchains/riscv-tools/riscv-isa-sim

# 4. espresso. Without it on PATH, Chisel falls back to its QMC minimizer, which runs out of
#    memory on Saturn's instruction decoder.
git submodule update --init generators/constellation
git -C generators/constellation submodule update --init espresso
cmake -S generators/constellation/espresso -B "$TOOLS/espresso-build" -DBUILD_DOC=OFF \
  -DCMAKE_INSTALL_PREFIX="$TOOLS/espresso"
cmake --build "$TOOLS/espresso-build" --target install -j"$JOBS"
rm -rf "$TOOLS/espresso-build"

# 5. Spike's libfesvr and libriscv, which the simulator links against ($RISCV/lib)
export RISCV="$TOOLS/riscv"
mkdir -p toolchains/riscv-tools/riscv-isa-sim/build
(
  cd toolchains/riscv-tools/riscv-isa-sim/build
  ../configure --prefix="$RISCV"
  make -j"$JOBS"
  make install
)

# 6. The configuration: Saturn's MINV128D64RocketConfig with the hypervisor extension, Sv48 and
#    29 HPM counters. The broadcast coherence manager (instead of the L2) and the removal of the
#    debug module make the model about 1.7x faster than the REFV256D128 SoC and do not change
#    the core.
cat >generators/chipyard/src/main/scala/config/ACTConfigs.scala <<'EOF'
package chipyard

import org.chipsalliance.cde.config.Config

class ACTRocketSaturnHConfig extends Config(
  new chipyard.config.WithNPerfCounters(29) ++
  new freechips.rocketchip.rocket.WithHypervisor ++
  new freechips.rocketchip.rocket.WithSV48 ++
  new chipyard.config.WithBroadcastManager ++
  new chipyard.config.WithNoDebug ++
  new chipyard.MINV128D64RocketConfig)
EOF

# 7. Elaborate and verilate
make -C sims/verilator -j"$JOBS" CONFIG="$CONFIG" JAVA_HEAP_SIZE="${JAVA_HEAP_SIZE:-12G}"

install -m 0755 "sims/verilator/simulator-chipyard.harness-$CONFIG" "$INSTALL_DIR/bin/simulator-rocket-saturn-h"
install -m 0755 "$SCRIPT_DIR/run-rocket.sh" "$INSTALL_DIR/bin/run-rocket.sh"

# The simulator needs only the shared libraries in $RISCV/lib at run time; drop everything else.
cd "$INSTALL_DIR"
rm -rf chipyard "$TOOLS/verilator" "$TOOLS/jdk" "$TOOLS/firtool" "$TOOLS/espresso" \
  "${RISCV:?}/bin" "${RISCV:?}/include" "${RISCV:?}/lib/pkgconfig" "${RISCV:?}"/lib/*.a
