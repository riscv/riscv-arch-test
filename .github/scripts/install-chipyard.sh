#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Build the Chipyard Verilator simulator of one ACT configuration for CI:
#   rocket  Rocket + Saturn + H (ACTRocketSaturnHConfig)
#   boom    BOOM v3, 2-wide (ACTMediumBoomV3Config)
# Usage: install-chipyard.sh <install-dir> [rocket|boom]
#        Without a core, the core comes from the install directory's name: CI installs each
#        simulator in a directory named after its config/cores directory, so each job builds and
#        caches only its own core.
# Cache key derives from sha256(this file); bump the pins below to invalidate. The patch
# checksums are pinned here too, so a changed patch also changes the key.
#
# Chipyard's own build-setup.sh installs a conda environment and a RISC-V toolchain; neither is
# needed to build a Verilator simulator, so this script installs only what the build uses:
# Verilator, a JDK for sbt, CIRCT firtool, espresso, and Spike's libfesvr/libriscv.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${1:?Usage: install-chipyard.sh <install-dir> [rocket|boom]}"
mkdir -p "$INSTALL_DIR/bin"
INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd)"
CORE="${2:-$(basename "$INSTALL_DIR")}"
JOBS="${JOBS:-$(nproc)}"

CHIPYARD_REPO="https://github.com/ucb-bar/chipyard.git"
CHIPYARD_COMMIT="0acc1e1de2d3284bcd4d876956932a013ffe1949" # 1.14.0
VERILATOR_VERSION="v5.036"
FIRTOOL_VERSION="1.75.0" # conda-reqs/circt.json at the pinned Chipyard commit
JDK_URL="https://api.adoptium.net/v3/binary/version/jdk-17.0.16%2B8/linux/x64/jdk/hotspot/normal/eclipse"

case "$CORE" in
rocket)
  # Chipyard 1.14.0 with its rocket-chip, Saturn master instead of Chipyard's Saturn pin, and
  # four local patches (see config/cores/rocket/README.md), each "<generator> <sha256> <file>".
  SATURN_COMMIT="8ef05c9c6044f05750c49e166a784ef8fbdcb883" # saturn-vectors master, 2026-09-02
  PATCHES=(
    # rocket-chip PR #3820 at its head commit d1d2c5e78138ddda9d439be0bb3081f107416ab9
    # (https://github.com/chipsalliance/rocket-chip/pull/3820): the FPU hands .vf scalars to the
    # vector unit as the full 64-bit register, so NaN-boxed single and half values keep their box.
    # Without it, Saturn master (Saturn PR #88) turns every NaN-boxed single or half .vf scalar
    # into the canonical NaN.
    "rocket-chip cc402d03d5d1f8f057231c237c78d2ee0b4d6fd89bd5b990082da9135c1385a7 rocket-chip-pr3820-d1d2c5e7.patch"
    # rocket-chip rocket/TLB.scala: the superpage refill writes the entry that hit (waddr), as the
    # sectored refill does. Without it, a VS/VU access whose VS-stage leaf is a 2 MiB or 1 GiB page
    # and whose G-stage translation faults neither retires nor traps. No upstream issue or PR.
    "rocket-chip a0adf68d71ccf5caba8dc4674384eceaa2fd3421ebcce2bce8fed59928658d00 rocket-chip-tlb-superpage-gpa.patch"
    # rocket-chip rocket/CSR.scala: implement htimedelta (and htimedeltah on RV32) with the
    # hypervisor extension. Without it every access raises an illegal-instruction exception, and
    # every ACT test that runs below M-mode traps at the htimedelta write in its boot code. No
    # upstream issue or PR.
    "rocket-chip 2f7867a8092987d2f464fc01972031bb1e34683b99481528341a205af6263bc0 rocket-chip-htimedelta.patch"
    # Saturn backend/SpecialSequencer.scala: clear the permute sequencer's valid on acc_done only
    # while it holds an instruction (https://github.com/ucb-bar/saturn-vectors/issues/74). Without
    # it, a stale acc/acc_done pair drops a slide or reduction at dispatch and the vector unit
    # deadlocks.
    "saturn 17a31e3bcef3e556f34b1ae362862e29b15dad579e39890e766b1b79398d73a1 saturn-acc-done-valid.patch"
  )
  init_generators() {
    ./scripts/init-submodules-no-riscv-tools.sh --saturn
    git -C generators/saturn fetch origin "$SATURN_COMMIT"
    git -C generators/saturn checkout --detach "$SATURN_COMMIT"
  }
  # Saturn's MINV128D64RocketConfig with the hypervisor extension, Sv48 and 29 HPM counters.
  CONFIG="ACTRocketSaturnHConfig"
  CONFIG_FRAGMENTS="
  new chipyard.config.WithNPerfCounters(29) ++
  new freechips.rocketchip.rocket.WithHypervisor ++
  new freechips.rocketchip.rocket.WithSV48 ++"
  BASE_CONFIG="chipyard.MINV128D64RocketConfig"
  ;;
boom)
  # Chipyard 1.14.0 with the BOOM and rocket-chip it pins, and one local patch (see
  # config/cores/boom/README.md).
  BOOM_COMMIT="5223e44cfeb26f41380057a2eb4d651197475f69" # generators/boom at Chipyard 1.14.0
  PATCHES=(
    # BOOM lsu/dcache.scala: drop the assertion that stops the simulation when 100 SCs in a row
    # fail at one address. A failing SC is legal, and the Zalrsc tests retry SCs that must fail
    # (outside the reservation set) 100 times.
    "boom 61032e1c79d0dde4fa5d5e4270e83980dd42336f74bdacc08a12f025c76ae7b5 boom-sc-fail-assert.patch"
  )
  init_generators() {
    ./scripts/init-submodules-no-riscv-tools.sh
    test "$(git -C generators/boom rev-parse HEAD)" = "$BOOM_COMMIT"
  }
  # Chipyard's MediumBoomV3Config (2-wide BOOM v3).
  CONFIG="ACTMediumBoomV3Config"
  CONFIG_FRAGMENTS=""
  BASE_CONFIG="chipyard.MediumBoomV3Config"
  ;;
*)
  echo "install-chipyard.sh: give the core (rocket or boom) as the second argument" >&2
  exit 2
  ;;
esac
PATCH_DIR="$SCRIPT_DIR/../../config/cores/$CORE/patches"

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

# 3. Chipyard at the pinned commit, with the generators the core needs, patched
git init "$INSTALL_DIR/chipyard"
cd "$INSTALL_DIR/chipyard"
git remote add origin "$CHIPYARD_REPO"
git fetch --depth 1 origin "$CHIPYARD_COMMIT"
git checkout FETCH_HEAD
init_generators
for patch in "${PATCHES[@]}"; do
  read -r generator sum file <<<"$patch"
  echo "$sum  $PATCH_DIR/$file" | sha256sum -c -
  git -C "generators/$generator" apply "$PATCH_DIR/$file"
done
git submodule update --init --depth 1 toolchains/riscv-tools/riscv-isa-sim

# 4. espresso. Without it on PATH, Chisel falls back to its QMC minimizer, which runs out of
#    memory on large decoders such as Saturn's.
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

# 6. The configuration. The broadcast coherence manager (instead of the L2) and the removal of
#    the debug module make the model faster (Rocket + Saturn: about 1.7x faster than the
#    REFV256D128 SoC) and do not change the core.
cat >generators/chipyard/src/main/scala/config/ACTConfigs.scala <<ACT_CONFIG
package chipyard

import org.chipsalliance.cde.config.Config

class $CONFIG extends Config($CONFIG_FRAGMENTS
  new chipyard.config.WithBroadcastManager ++
  new chipyard.config.WithNoDebug ++
  new $BASE_CONFIG)
ACT_CONFIG

# 7. Elaborate and verilate
make -C sims/verilator -j"$JOBS" CONFIG="$CONFIG" JAVA_HEAP_SIZE="${JAVA_HEAP_SIZE:-12G}"

install -m 0755 "sims/verilator/simulator-chipyard.harness-$CONFIG" "$INSTALL_DIR/bin/simulator"
install -m 0755 "$SCRIPT_DIR/run-chipyard.sh" "$INSTALL_DIR/bin/run-chipyard.sh"

# The simulator needs only the shared libraries in $RISCV/lib at run time; drop everything else.
cd "$INSTALL_DIR"
rm -rf chipyard "$TOOLS/verilator" "$TOOLS/jdk" "$TOOLS/firtool" "$TOOLS/espresso" \
  "${RISCV:?}/bin" "${RISCV:?}/include" "${RISCV:?}/lib/pkgconfig" "${RISCV:?}"/lib/*.a
