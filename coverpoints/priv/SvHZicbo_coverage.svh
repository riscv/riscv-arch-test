///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Cache-block operations from VS-mode and VU-mode: the henvcfg enables, each VS-stage and G-stage
// PTE under two-stage translation, and PMP on the final address.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVHZICBO

// Guest virtual addresses of SvHZicbo.py's cases: VS-stage cases use VS_SV39/VS_SV32 data_va, and
// G-stage cases SV39X4/SV32X4 data_va through a VS-stage identity superpage.
`ifdef UDB_MXLEN_64
  `define SVHZICBO_GVA_SUPERPAGE(addr) addr[63:30]
  `define SVHZICBO_VS_SUPERPAGE 5
  `define SVHZICBO_G_SUPERPAGE 11
`else
  `define SVHZICBO_GVA_SUPERPAGE(addr) addr[31:22]
  `define SVHZICBO_VS_SUPERPAGE 'h241
  `define SVHZICBO_G_SUPERPAGE 'h341
`endif

covergroup SvHZicbo_cg with function sample(ins_t ins);
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
  vsatp_paged: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
    bins paged = {[1:15]};
  }
  hgatp_paged: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
    bins paged = {[1:15]};
  }
  vs_stage: coverpoint `SVHZICBO_GVA_SUPERPAGE(ins.current.rs1_val) {
    bins vs = {`SVHZICBO_VS_SUPERPAGE};
  }
  g_stage: coverpoint `SVHZICBO_GVA_SUPERPAGE(ins.current.rs1_val) {
    bins g = {`SVHZICBO_G_SUPERPAGE};
  }
  stage: coverpoint `SVHZICBO_GVA_SUPERPAGE(ins.current.rs1_val) {
    bins vs = {`SVHZICBO_VS_SUPERPAGE};
    bins g  = {`SVHZICBO_G_SUPERPAGE};
  }

  // The trap the CBO takes, from the mcause the trace shows it writing
  vs_pte_outcome: coverpoint {ins.current.csr_wb[CSR_MCAUSE], ins.current.csr[CSR_MCAUSE][4:0]} {
    wildcard bins no_fault = {6'b0?????};
    bins store_page_fault  = {6'b101111};
  }
  g_pte_outcome: coverpoint {ins.current.csr_wb[CSR_MCAUSE], ins.current.csr[CSR_MCAUSE][4:0]} {
    wildcard bins no_fault       = {6'b0?????};
    bins store_guest_page_fault  = {6'b110111};
  }
  gpa_outcome: coverpoint {ins.current.csr_wb[CSR_MCAUSE], ins.current.csr[CSR_MCAUSE][4:0]} {
    bins store_guest_page_fault = {6'b110111};
    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
      bins store_access_fault   = {6'b100111};
    `endif
  }
  no_fault: coverpoint ins.current.csr_wb[CSR_MCAUSE] {
    bins no_fault = {0};
  }
  store_access_fault: coverpoint {ins.current.csr_wb[CSR_MCAUSE], ins.current.csr[CSR_MCAUSE][4:0]} {
    bins store_access_fault = {6'b100111};
  }
  // mtinst holds the pseudoinstruction of a guest-page fault on an implicit VS-stage page-table read
  pseudoinstruction: coverpoint ins.current.csr[CSR_MTINST] iff (ins.current.csr_wb[CSR_MTINST]) {
    bins read = {'h2000, 'h3000};
  }
  // In VS-mode the trace logs vsstatus as sstatus
  vsstatus_sum: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sum") {
    bins set = {1};
  }
  // PMP entry 0 covers the test page with no permissions, or with read permission only
  pmp_xwr: coverpoint ins.current.csr[CSR_PMPCFG0][7:0] {
    bins none = {8'b00011000};
    bins r    = {8'b00011001};
  }

  cp_vs_pte:          cross priv_mode_vs_vu, cbo, vs_stage, vs_pte_outcome, vsatp_paged, hgatp_paged;
  cp_vs_sum:          cross priv_mode_vs, cbo, vs_stage, vsstatus_sum, no_fault;
  cp_vs_gpa:          cross priv_mode_vs_vu, cbo, vs_stage, gpa_outcome;
  cp_vs_gpa_implicit: cross priv_mode_vs_vu, cbo, vs_stage, pseudoinstruction;
  cp_g_pte:           cross priv_mode_vs_vu, cbo, g_stage, g_pte_outcome, vsatp_paged, hgatp_paged;
  `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
    cp_g_pa:          cross priv_mode_vs_vu, cbo, g_stage, store_access_fault;
  `endif
  cp_pmp:             cross priv_mode_vs_vu, cbo, stage, pmp_xwr;
endgroup

// CBOs in VS-mode and VU-mode across the menvcfg, henvcfg and senvcfg enables, with translation Bare
covergroup SvHZicbo_envcfg_cg with function sample(ins_t ins);
  option.per_instance = 0;
  `include "general/RISCV_coverage_standard_coverpoints.svh"

  inval: coverpoint ins.current.insn {
    wildcard bins inval = {CBO_INVAL};
  }
  clean_flush: coverpoint ins.current.insn {
    wildcard bins clean = {CBO_CLEAN};
    wildcard bins flush = {CBO_FLUSH};
  }
  zero: coverpoint ins.current.insn {
    wildcard bins zero = {CBO_ZERO};
  }
  menvcfg_cbie: coverpoint ins.prev.csr[CSR_MENVCFG][5:4] {
    bins off   = {2'b00};
    bins flush = {2'b01};
    bins inval = {2'b11};
  }
  henvcfg_cbie: coverpoint ins.prev.csr[CSR_HENVCFG][5:4] {
    bins off   = {2'b00};
    bins flush = {2'b01};
    bins inval = {2'b11};
  }
  senvcfg_cbie: coverpoint ins.prev.csr[CSR_SENVCFG][5:4] {
    bins off   = {2'b00};
    bins flush = {2'b01};
    bins inval = {2'b11};
  }
  menvcfg_cbcfe: coverpoint ins.prev.csr[CSR_MENVCFG][6] {
    bins off = {0};
    bins on  = {1};
  }
  henvcfg_cbcfe: coverpoint ins.prev.csr[CSR_HENVCFG][6] {
    bins off = {0};
    bins on  = {1};
  }
  senvcfg_cbcfe: coverpoint ins.prev.csr[CSR_SENVCFG][6] {
    bins off = {0};
    bins on  = {1};
  }
  menvcfg_cbze: coverpoint ins.prev.csr[CSR_MENVCFG][7] {
    bins off = {0};
    bins on  = {1};
  }
  henvcfg_cbze: coverpoint ins.prev.csr[CSR_HENVCFG][7] {
    bins off = {0};
    bins on  = {1};
  }
  senvcfg_cbze: coverpoint ins.prev.csr[CSR_SENVCFG][7] {
    bins off = {0};
    bins on  = {1};
  }
  vsatp_bare: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
    bins bare = {0};
  }

  `ifdef ZICBOM_SUPPORTED
    cp_cbie_vs:  cross priv_mode_vs, inval, menvcfg_cbie, henvcfg_cbie, vsatp_bare;
    cp_cbie_vu:  cross priv_mode_vu, inval, menvcfg_cbie, henvcfg_cbie, senvcfg_cbie, vsatp_bare;
    cp_cbcfe_vs: cross priv_mode_vs, clean_flush, menvcfg_cbcfe, henvcfg_cbcfe, vsatp_bare;
    cp_cbcfe_vu: cross priv_mode_vu, clean_flush, menvcfg_cbcfe, henvcfg_cbcfe, senvcfg_cbcfe, vsatp_bare;
  `endif
  `ifdef ZICBOZ_SUPPORTED
    cp_cbze_vs:  cross priv_mode_vs, zero, menvcfg_cbze, henvcfg_cbze, vsatp_bare;
    cp_cbze_vu:  cross priv_mode_vu, zero, menvcfg_cbze, henvcfg_cbze, senvcfg_cbze, vsatp_bare;
  `endif
endgroup

function void svhzicbo_sample(int hart, int issue, ins_t ins);
  SvHZicbo_cg.sample(ins);
  SvHZicbo_envcfg_cg.sample(ins);
endfunction
