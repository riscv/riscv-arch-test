///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Standard Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_RV32PMP
`define COVER_RV64PMP

covergroup PMPZicbo_cg with function sample(ins_t ins, logic [7:0] pmpcfg [63:0], logic [14:0] pmp_hit, logic [XLEN-1:0] pmpaddr [62:0]);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    cfg_for_menvcfg: coverpoint ins.current.csr[12'h30A][7:4] {
        bins configuration = {4'b1111}; //menvcfg.CBIE, CBCFE, CBZE = 1
    }

    pmpaddr_region: coverpoint  ((pmpaddr[0] == (`REGIONSTART>>2)) &&
                                 (pmpaddr[1] == ((`REGIONSTART + 16'h1000) >>2))) {
        bins region = {1};
    }

    addr_in_region: coverpoint ins.current.rs1_val {
        bins address = {`REGIONSTART};
    }

    cbo_clean_instr: coverpoint ins.current.insn {
        wildcard bins cbo_clean = {32'b000000000001_?????_010_00000_0001111};
    }

    cbo_flush_instr: coverpoint ins.current.insn {
        wildcard bins cbo_flush = {32'b000000000010_?????_010_00000_0001111};
    }

    cbo_inval_instr: coverpoint ins.current.insn {
        wildcard bins cbo_inval = {32'b000000000000_?????_010_00000_0001111};
    }

    cbo_zero_instr: coverpoint ins.current.insn {
        wildcard bins cbo_zero = {32'b000000000100_?????_010_00000_0001111};
    }

    prefetch_i_instr: coverpoint ins.current.insn {
        wildcard bins prefetch_i_instr = {32'b???????_00000_?????_110_00000_0010011};
    }

    prefetch_r_instr: coverpoint ins.current.insn {
        wildcard bins prefetch_i_instr = {32'b???????_00001_?????_110_00000_0010011};
    }

    prefetch_w_instr: coverpoint ins.current.insn {
        wildcard bins prefetch_i_instr = {32'b???????_00011_?????_110_00000_0010011};
    }

    // TOR Regions ((6,5),(5,4),(4,3),(3,2),(2,1),(1,0))
  legal_lxwr: coverpoint {pmpcfg[1],pmpcfg[2],pmpcfg[3],pmpcfg[4],pmpcfg[5],pmpcfg[6],pmp_hit[5:0]} {
    wildcard bins cfg_l000 = {54'b????????????????????????????????????????10001000_100000};
    wildcard bins cfg_l001 = {54'b????????????????????????????????10001001????????_?10000};
    wildcard bins cfg_l011 = {54'b????????????????????????10001011????????????????_??1000};
    wildcard bins cfg_l100 = {54'b????????????????10001100????????????????????????_???100};
    wildcard bins cfg_l101 = {54'b????????10001101????????????????????????????????_????10};
    wildcard bins cfg_l111 = {54'b10001111????????????????????????????????????????_?????1};
  }

  wr_combinations: coverpoint {pmpcfg[1],pmpcfg[0]} {
    bins cfg_l000 = {16'b10001000_10001111};
    bins cfg_l001 = {16'b10001001_10001111};
    bins cfg_l011 = {16'b10001011_10001111};
  }

    cp_prefetch_w: cross priv_mode_m, legal_lxwr, cfg_for_menvcfg, prefetch_w_instr, addr_in_region;
    cp_prefetch_r: cross priv_mode_m, legal_lxwr, cfg_for_menvcfg, prefetch_r_instr, addr_in_region;
    cp_prefetch_i: cross priv_mode_m, legal_lxwr, cfg_for_menvcfg, prefetch_i_instr, addr_in_region;

    cp_cbo_zero:  cross priv_mode_m, wr_combinations, pmpaddr_region, cfg_for_menvcfg, cbo_zero_instr;
    cp_cbo_inval: cross priv_mode_m, wr_combinations, pmpaddr_region, cfg_for_menvcfg, cbo_inval_instr;
    cp_cbo_flush: cross priv_mode_m, wr_combinations, pmpaddr_region, cfg_for_menvcfg, cbo_flush_instr;
    cp_cbo_clean: cross priv_mode_m, wr_combinations, pmpaddr_region, cfg_for_menvcfg, cbo_clean_instr;

endgroup

function void pmpzicbo_sample(int hart, int issue, ins_t ins);

  logic [7:0] pmpcfg [63:0];
  logic [XLEN-1:0] pmpaddr [62:0];
  logic [14:0] pmp_hit;   // for first 15 Regions

  `ifdef XLEN32
    // Each pmpcfg CSR holds 4 region configs in 32-bit (4x 8-bit)
    for (int i = 0; i < 16; i++) begin
      logic [31:0] cfg_word = ins.current.csr[12'h3A0 + i];
      pmpcfg[i*4 + 0] = cfg_word[7:0];
      pmpcfg[i*4 + 1] = cfg_word[15:8];
      pmpcfg[i*4 + 2] = cfg_word[23:16];
      pmpcfg[i*4 + 3] = cfg_word[31:24];
    end
  `elsif XLEN64
    // Each pmpcfg CSR holds 8 region configs in 64-bit (8x 8-bit)
    for (int i = 0; i < 8; i++) begin
      logic [63:0] cfg_word = ins.current.csr[12'h3A0 + 2*i];
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
    pmpaddr[j] = ins.current.csr[12'h3B0 + j];
  end

  for (int k = 0; k < 15; k++) begin  // Check for first 15 PMP regions
    pmp_hit[k] = (pmpaddr[k] == `STANDARD_REGION) || (pmpaddr[k] == `NON_STANDARD_REGION);
  end

  PMPZicbo_cg.sample(ins, pmpcfg, pmp_hit, pmpaddr);
endfunction
