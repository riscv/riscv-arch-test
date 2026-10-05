///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Standard Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_PMPZALRSC
`include "PMP_partial.svh"

covergroup PMPZalrsc_cg with function sample(ins_t ins,logic [7:0] pmpcfg [63:0],logic [14:0] pmp_hit, pmp_partial_t partial);
  option.per_instance = 0;
  `include  "general/RISCV_coverage_standard_coverpoints.svh"

  // The region-under-test sits at a fixed offset inside a 0x4000-aligned .data block, but its
  // absolute address drifts with test code size, so match on the invariant low bits
  // (PMP_ADDR_LOWMASK) instead of the absolute PMP_REGION_START.
  rs1_in_region: coverpoint (ins.current.rs1_val & `PMP_ADDR_LOWMASK) {
    bins at_region = {`PMP_SPECIAL_REGION_START & `PMP_ADDR_LOWMASK};
  }

  atomic_intrs: coverpoint ins.current.insn {
    wildcard bins lr_w  = {LR_W};
    wildcard bins sc_w  = {SC_W};
    `ifdef UDB_MXLEN_64
      wildcard bins lr_d  = {LR_D};
      wildcard bins sc_d  = {SC_D};
    `endif
  }

  legal_lxwr: coverpoint {pmpcfg[0],pmpcfg[1],pmpcfg[2],pmpcfg[3],pmpcfg[4],pmpcfg[5],pmp_hit[5:0]} {
    wildcard bins cfg_l000 = {54'b????????????????????????????????????????10011000_100000};
    wildcard bins cfg_l001 = {54'b????????????????????????????????10011001????????_?10000};
    wildcard bins cfg_l011 = {54'b????????????????????????10011011????????????????_??1000};
    wildcard bins cfg_l100 = {54'b????????????????10011100????????????????????????_???100};
    wildcard bins cfg_l101 = {54'b????????10011101????????????????????????????????_????10};
    wildcard bins cfg_l111 = {54'b10011111????????????????????????????????????????_?????1};
  }

  cp_cfg_RW: cross priv_mode_m, legal_lxwr, atomic_intrs, rs1_in_region;

  // Partial matches (see PMP_partial.svh): the deciding entry matches only some bytes of the access.
  `ifdef UDB_MXLEN_64
    partial_lrsc_d: coverpoint ins.current.insn {
      type_option.weight = 0;
      wildcard bins lr_d = {LR_D};
      wildcard bins sc_d = {SC_D};
    }
  `endif

  partial_kind: coverpoint partial.kind {
    type_option.weight = 0;
    bins lower = {PMP_PARTIAL_LOWER};
    bins upper = {PMP_PARTIAL_UPPER};
    bins both  = {PMP_PARTIAL_BOTH};
  }

  partial_aligned: coverpoint partial.align {
    type_option.weight = 0;
    bins aligned = {PMP_ACCESS_ALIGNED};
  }

  partial_lock: coverpoint partial.cfg[7] {
    type_option.weight = 0;
    bins unlocked = {1'b0};
    bins locked   = {1'b1};
  }

  partial_amode: coverpoint partial.cfg[4:3] {
    type_option.weight = 0;
    `ifdef UDB_PMP_NA4_SUPPORTED
      bins na4 = {2'b10};
    `endif
    `ifdef UDB_PMP_TOR_SUPPORTED
      bins tor = {2'b01};
    `endif
  }

  `ifdef PMP_PARTIAL_ENTRIES
    `ifdef UDB_MXLEN_64
      `ifdef UDB_PMP_GRANULARITY_2
        cp_partial_match: cross priv_mode_m, partial_lrsc_d, partial_aligned, partial_amode, partial_lock, partial_kind ;
      `endif
    `endif
  `endif

endgroup

function void pmpzalrsc_sample(int hart, int issue, ins_t ins);

  logic [7:0] pmpcfg [63:0];
  logic [`UDB_MXLEN-1:0] pmpaddr [62:0];
  logic [14:0] pmp_hit;   // for first 15 Regions

  `ifdef UDB_MXLEN_32
      // Each pmpcfg CSR holds 4 region configs in 32-bit (4x 8-bit)
      for (int i = 0; i < 16; i++) begin
          logic [31:0] cfg_word = get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_PMPCFG0 + i, "pmpcfg", "pmpcfg");
          pmpcfg[i*4 + 0] = cfg_word[7:0];
          pmpcfg[i*4 + 1] = cfg_word[15:8];
          pmpcfg[i*4 + 2] = cfg_word[23:16];
          pmpcfg[i*4 + 3] = cfg_word[31:24];
      end
  `elsif UDB_MXLEN_64
      // Each pmpcfg CSR holds 8 region configs in 64-bit (8x 8-bit)
    for (int i = 0; i < 8; i++) begin
        logic [63:0] cfg_word = get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_PMPCFG0 + 2*i, "pmpcfg", "pmpcfg");
        pmpcfg[i*8 + 0] = cfg_word[7:0];
        pmpcfg[i*8 + 1] = cfg_word[15:8];
        pmpcfg[i*8 + 2] = cfg_word[23:16];
        pmpcfg[i*8 + 3] = cfg_word[31:24];
        pmpcfg[i*8 + 4] = cfg_word[39:32];
        pmpcfg[i*8 + 5] = cfg_word[47:40];
        pmpcfg[i*8 + 6] = cfg_word[55:48];
        pmpcfg[i*8 + 7] = cfg_word[63:56];
    end
  `endif

  for (int j = 0; j < 63; j++) begin
    pmpaddr[j] = get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_PMPADDR0 + j, "pmpaddr", "pmpaddr");
  end

  for (int k = 0; k < 15; k++) begin  // Check for first 15 PMP regions
    // Match on the code-size-invariant low bits; the absolute region address drifts with test size.
    pmp_hit[k] = ((pmpaddr[k] & `PMP_PMPADDR_LOWMASK) == (`SPECIAL_STANDARD_REGION & `PMP_PMPADDR_LOWMASK)) ||
                 ((pmpaddr[k] & `PMP_PMPADDR_LOWMASK) == (`SPECIAL_NON_STANDARD_REGION & `PMP_PMPADDR_LOWMASK));
  end

  PMPZalrsc_cg.sample(ins, pmpcfg, pmp_hit, pmp_partial(ins));
endfunction
