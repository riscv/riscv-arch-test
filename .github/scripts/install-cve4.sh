#!/usr/bin/env bash
# Marin Radic mradic07@gmail.com
# SPDX-License-Identifier: Apache-2.0
# Install cve4 testbenches (Verilator) for CI: cv32e40p-dv, cv32e40x-dv, and the CV32E40S
# in cv32e40x-dv's core testbench.
# Usage: install-cve4.sh <install-dir>
# Cache key derives from sha256(this file)[:12]; bump versions/commits below to invalidate.
# The cache key does not cover cv32e40s_tb_wrapper.sv: bump the revision below when it changes.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-cve4.sh <install-dir>}"
CVE4_DV_REPO="https://github.com/openhwfoundation/cv32e40p-dv-review.git"
CVE4_DV_COMMIT="89ad543d8709f6dae55c9a91cd2d14f4b25ac348"
CVE40X_DV_REPO="https://github.com/openhwfoundation/cv32e40x-dv.git"
CVE40X_DV_COMMIT="93ce70f1ae2ab2e66716e0c5648d27e67e161c2f"
CVE40X_CORE_HASH="d952cd63bc1b4eb58cd893c28ef8283c781e345e" # pin cv32e40x RTL
CVE40S_REPO="https://github.com/openhwfoundation/cv32e40s.git"
CVE40S_COMMIT="9d9cae78b01a11458953133d1173c61933a2ba86"
# cv32e40s_tb_wrapper.sv revision: 1
VERILATOR_VERSION="v5.052"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# 5. Clone cv32e40x-dv at its pinned commit (fetch by SHA, same pattern as above).
git init "$INSTALL_DIR/cv32e40x-dv"
(
  cd "$INSTALL_DIR/cv32e40x-dv"
  git remote add origin "$CVE40X_DV_REPO"
  git fetch --depth 1 origin "$CVE40X_DV_COMMIT"
  git checkout FETCH_HEAD
)

# 6. Verilate both cv32e40x configs (reuses Verilator built above; RTL pinned).
for cfg in rv32imc rv32imcab; do
  make -C "$INSTALL_DIR/cv32e40x-dv/sim/core" \
    verilate \
    CV_CORE_CONFIG="$cfg" \
    CV_CORE_HASH="$CVE40X_CORE_HASH" \
    CV_SW_TOOLCHAIN=/usr/local \
    CV_SW_PREFIX=riscv64-unknown-elf- \
    -j"$(nproc)"
done

# 7. Install the cv32e40x per-test wrapper.
install -m 0755 "$INSTALL_DIR/cv32e40x-dv/.github/scripts/run-cv32e40x.sh" \
  "$INSTALL_DIR/bin/run-cv32e40x.sh"

# 8. Clone the cv32e40s RTL at its pinned commit.
git init "$INSTALL_DIR/cv32e40s"
(
  cd "$INSTALL_DIR/cv32e40s"
  git remote add origin "$CVE40S_REPO"
  git fetch --depth 1 origin "$CVE40S_COMMIT"
  git checkout FETCH_HEAD
)

# 9. Verilate each cv32e40s config in cv32e40x-dv's core testbench, with
# cv32e40s_tb_wrapper.sv in place of cv32e40x_tb_wrapper.sv. The compile flags follow
# cv32e40x-dv's sim/core Makefile; the defines select the core parameters (see the wrapper).
TB="$INSTALL_DIR/cv32e40x-dv/tb/core"
TB_OUT="$INSTALL_DIR/cv32e40s-tb"
mkdir -p "$TB_OUT"
sed 's/cv32e40x_tb_wrapper/cv32e40s_tb_wrapper/g' "$TB/tb_top.sv" >"$TB_OUT/tb_top.sv"
export DESIGN_RTL_DIR="$INSTALL_DIR/cv32e40s/rtl" # used by cv32e40s_manifest.flist
declare -A CVE40S_DEFINES=(
  ["rv32imc"]=""
  ["rv32imc-pma"]="+define+CV32E40S_PMA"
  ["rv32imc-pma-pmp"]="+define+CV32E40S_PMA +define+CV32E40S_PMP"
  ["rv32imcb-pma-pmp"]="+define+CV32E40S_RVB +define+CV32E40S_PMA +define+CV32E40S_PMP"
)
for cfg in "${!CVE40S_DEFINES[@]}"; do
  # shellcheck disable=SC2086 # the defines are separate arguments
  verilator --cc --sv --exe --build --main --timing -j "$(nproc)" \
    --Wno-lint --Wno-UNOPTFLAT --Wno-MODDUP -Wno-BLKANDNBLK -Wno-COMBDLY -Wno-SYMRSVDWORD \
    +define+COREV_ASSERT_OFF --x-assign unique --x-initial unique \
    --top-module tb_top \
    -f "$INSTALL_DIR/cv32e40s/cv32e40s_manifest.flist" \
    "$TB/tb_riscv/include/perturbation_defines.sv" "$TB_OUT/tb_top.sv" "$SCRIPT_DIR/cv32e40s_tb_wrapper.sv" \
    "$TB/mm_ram.sv" "$TB/dp_ram.sv" "$TB/tb_riscv/riscv_rvalid_stall.sv" "$TB/tb_riscv/riscv_gnt_stall.sv" \
    ${CVE40S_DEFINES[$cfg]} \
    --Mdir "$TB_OUT/obj_dir" -CFLAGS "-std=gnu++14 -O2"
  mkdir -p "$TB_OUT/$cfg"
  cp "$TB_OUT/obj_dir/Vtb_top" "$TB_OUT/$cfg/Vtb_top"
  rm -rf "$TB_OUT/obj_dir"
done

# 10. Install the cv32e40s per-test wrapper.
install -m 0755 "$SCRIPT_DIR/run-cv32e40s.sh" "$INSTALL_DIR/bin/run-cv32e40s.sh"
