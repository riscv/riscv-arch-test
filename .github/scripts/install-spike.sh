#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Jordan Carlin jcarlin@hmc.edu April 2026
# Install Spike RISC-V ISA Simulator from source
# Usage: install-spike.sh <install-dir>
# Update SPIKE_COMMIT to rebuild with a newer version (cache key is derived from this script's hash).

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-spike.sh <install-dir>}"
SPIKE_COMMIT="19609434bb3d83448eec8796e8f0367c868efbda"

git clone https://github.com/riscv/riscv-isa-sim.git
cd riscv-isa-sim
git checkout "$SPIKE_COMMIT"
# Backport RV32 hedelegh until the pinned upstream revision includes it.
# Keep the patch here so a backport change invalidates the simulator cache.
git apply <<'SPIKE_HEDELEGH_FIX'
diff --git a/riscv/csr_init.cc b/riscv/csr_init.cc
index aa052198..aec4761c 100644
--- a/riscv/csr_init.cc
+++ b/riscv/csr_init.cc
@@ -276,6 +276,8 @@ void state_t::csr_init(processor_t* const proc, reg_t max_isa)
     (proc->extension_enabled(EXT_ZICNTR)?
      (1 << CAUSE_HARDWARE_ERROR_FAULT) : 0);
   add_hypervisor_csr(CSR_HEDELEG, hedeleg = std::make_shared<masked_csr_t>(proc, CSR_HEDELEG, hedeleg_mask, 0));
+  if (xlen == 32)
+    add_hypervisor_csr(CSR_HEDELEGH, std::make_shared<rv32_high_csr_t>(proc, CSR_HEDELEGH, hedeleg));
   add_hypervisor_csr(CSR_HCOUNTEREN, hcounteren = std::make_shared<masked_csr_t>(proc, CSR_HCOUNTEREN, counteren_mask, 0));
   htimedelta = std::make_shared<basic_csr_t>(proc, CSR_HTIMEDELTA, 0);
   if (xlen == 32) {
SPIKE_HEDELEGH_FIX
mkdir build && cd build
../configure --prefix="$INSTALL_DIR"
make -j"$(nproc)"
make install
