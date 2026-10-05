///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Standard Covergroups
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_PMPZACAS
`include "PMP_partial.svh"

// Aligned AMOs are one memory operation even when wider than XLEN (amocas.d on RV32, amocas.q), and so is a
// misaligned AMO inside a misaligned atomicity granule.
covergroup PMPZacas_cg with function sample(ins_t ins, pmp_partial_t partial);
  option.per_instance = 0;
  `include  "general/RISCV_coverage_standard_coverpoints.svh"

  amocas_d: coverpoint ins.current.insn {
    type_option.weight = 0;
    wildcard bins amocas_d = {AMOCAS_D};
  }

  `ifdef UDB_MXLEN_64
    amocas_q: coverpoint ins.current.insn {
      type_option.weight = 0;
      wildcard bins amocas_q = {AMOCAS_Q};
    }
  `endif

  amocas_wd: coverpoint ins.current.insn {
    type_option.weight = 0;
    wildcard bins amocas_w = {AMOCAS_W};
    wildcard bins amocas_d = {AMOCAS_D};
  }

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

  partial_in_granule16: coverpoint partial.align {
    type_option.weight = 0;
    bins in_granule16 = {PMP_ACCESS_IN_GRANULE16};
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

  partial_amode_quad: coverpoint partial.cfg[4:3] {
    type_option.weight = 0;
    `ifdef UDB_PMP_NAPOT_SUPPORTED
      bins napot = {2'b11};
    `endif
    `ifdef UDB_PMP_TOR_SUPPORTED
      bins tor = {2'b01};
    `endif
  }

  partial_tor: coverpoint partial.cfg[4:3] {
    type_option.weight = 0;
    bins tor = {2'b01};
  }

  `ifdef PMP_PARTIAL_ENTRIES
    `ifdef UDB_PMP_GRANULARITY_2
      cp_partial_match_d: cross priv_mode_m, amocas_d, partial_aligned, partial_amode, partial_lock, partial_kind ;
    `endif
    `ifdef UDB_MXLEN_64
      `ifdef PMP_PARTIAL_GRAIN_8
        cp_partial_match_q: cross priv_mode_m, amocas_q, partial_aligned, partial_amode_quad, partial_lock, partial_kind ;
      `endif
    `endif
  `endif

  `ifdef PMP_PARTIAL_ENTRIES
    `ifdef ZAMA16B_SUPPORTED
      `ifdef PMP_PARTIAL_GRAIN_8
        `ifdef UDB_PMP_TOR_SUPPORTED
          cp_misaligned_mag16: cross priv_mode_m, amocas_wd, partial_in_granule16, partial_tor, partial_lock, partial_kind ;
        `endif
      `endif
    `endif
  `endif

endgroup

function void pmpzacas_sample(int hart, int issue, ins_t ins);
  PMPZacas_cg.sample(ins, pmp_partial(ins));
endfunction
