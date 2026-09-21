#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Install the SERV servant testbench (Verilator) for CI.
# Usage: install-serv.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-serv.sh <install-dir>}"
SERV_REPO="https://github.com/olofk/serv.git"
SERV_COMMIT="f200eb2ed7b69ac1c6b8eddd47654522aeee5ce8"
# The M extension comes from an external accelerator that servant instantiates as `mdu_top`
# when the MDU define is set; SERV's own compliance flow adds the same library.
MDU_REPO="https://github.com/zeeshanrafique23/mdu.git"
MDU_COMMIT="8016099f24422e62fdd32c6f684a54cf4e4d868b"
VERILATOR_VERSION="v5.036"

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

# 2. Clone SERV and the MDU at the pinned commits
for spec in "serv:$SERV_REPO:$SERV_COMMIT" "mdu:$MDU_REPO:$MDU_COMMIT"; do
  name="${spec%%:*}"
  rest="${spec#*:}"
  url="${rest%:*}"
  sha="${rest##*:}"
  git init "$INSTALL_DIR/$name"
  (
    cd "$INSTALL_DIR/$name"
    git remote add origin "$url"
    git fetch --depth 1 origin "$sha"
    git checkout FETCH_HEAD
  )
done

# 3. Verilate servant_sim by hand.  fusesoc is not used: it needs a library registry and a
#    network fetch at build time, and the file list below is exactly what its verilator_tb
#    target passes through, with the same parameters SERV's own compliance flow uses
#    (width=1, compressed=1, with_csr=1, MDU=1, memsize=8 MiB).
#    Everything here is stock upstream RTL and the stock testbench: this port patches nothing.
mkdir -p "$INSTALL_DIR/act/obj"
(
  cd "$INSTALL_DIR/serv"
  verilator --cc --exe -Wno-lint -O3 --trace --top-module servant_sim \
    -Gmemsize=8388608 -Gcompressed=1 -Gwith_csr=1 -Gwidth=1 \
    +define+MDU=1 \
    bench/servant_sim.v \
    servant/servant.v servant/servant_ram.v servant/servant_gpio.v \
    servant/servant_timer.v servant/servant_mux.v \
    servile/servile.v servile/servile_arbiter.v servile/servile_mux.v \
    servile/servile_rf_mem_if.v \
    rtl/serv_aligner.v rtl/serv_alu.v rtl/serv_bufreg.v rtl/serv_bufreg2.v \
    rtl/serv_compdec.v rtl/serv_csr.v rtl/serv_ctrl.v rtl/serv_debug.v rtl/serv_decode.v \
    rtl/serv_immdec.v rtl/serv_mem_if.v rtl/serv_rf_if.v rtl/serv_rf_ram.v \
    rtl/serv_rf_ram_if.v rtl/serv_rf_top.v rtl/serv_state.v rtl/serv_top.v \
    "$INSTALL_DIR/mdu/rtl/mdu_top.v" \
    bench/servant_tb.cpp --Mdir "$INSTALL_DIR/act/obj"
  make -C "$INSTALL_DIR/act/obj" -f Vservant_sim.mk -j"$(nproc)"
)

# 4. Install the per-test runner
install -m 0755 "$(dirname "$0")/run-serv.sh" "$INSTALL_DIR/bin/run-serv.sh"
