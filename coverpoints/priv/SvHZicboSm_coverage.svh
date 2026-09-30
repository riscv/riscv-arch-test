///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// PMP on the final address of cache-block operations from VS-mode and VU-mode under two-stage translation.
// Written: David_Harris@hmc.edu 29 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVHZICBOSM

// Guest virtual addresses of SvHZicbo.py's cases, as in SvHZicbo_coverage.svh
`ifndef SVHZICBO_GVA_SUPERPAGE
  `ifdef UDB_MXLEN_64
    `define SVHZICBO_GVA_SUPERPAGE(addr) addr[63:30]
    `define SVHZICBO_VS_SUPERPAGE 5
    `define SVHZICBO_G_SUPERPAGE 11
  `else
    `define SVHZICBO_GVA_SUPERPAGE(addr) addr[31:22]
    `define SVHZICBO_VS_SUPERPAGE 'h241
    `define SVHZICBO_G_SUPERPAGE 'h341
  `endif
`endif

covergroup SvHZicboSm_cg with function sample(ins_t ins);
  option.per_instance = 0;
  `include "general/RISCV_coverage_standard_coverpoints.svh"

  cbo: coverpoint ins.current.insn {
    `ifdef ZICBOM_SUPPORTED
      wildcard bins clean = {CBO_CLEAN};
      wildcard bins flush = {CBO_FLUSH};
      wildcard bins inval = {CBO_INVAL};
    `endif
    `ifdef ZICBOZ_SUPPORTED
      wildcard bins zero = {CBO_ZERO};
    `endif
  }
  stage: coverpoint `SVHZICBO_GVA_SUPERPAGE(ins.current.rs1_val) {
    bins vs = {`SVHZICBO_VS_SUPERPAGE};
    bins g  = {`SVHZICBO_G_SUPERPAGE};
  }
  // PMP entry 0 covers the test page with no permissions, or with read permission only
  pmp_xwr: coverpoint ins.current.csr[CSR_PMPCFG0][7:0] {
    bins none = {8'b00011000};
    bins r    = {8'b00011001};
  }

  cp_pmp: cross priv_mode_vs_vu, cbo, stage, pmp_xwr;
endgroup

function void svhzicbosm_sample(int hart, int issue, ins_t ins);
  SvHZicboSm_cg.sample(ins);
endfunction
