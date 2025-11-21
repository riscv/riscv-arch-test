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

covergroup PMPZca_cg with function sample(ins_t ins, logic [7:0] pmpcfg [63:0], logic [14:0] pmp_hit, logic [XLEN-1:0] pmpaddr [62:0]);
  option.per_instance = 0;
  `include  "general/RISCV_coverage_standard_coverpoints.svh"

  addr_in_region: coverpoint (ins.current.rs1_val + ins.current.imm) {
    bins at_region = {`REGIONSTART};
  }

  standard_region: coverpoint ins.current.csr[12'h3B5] {
    bins standard_region = {`STANDARD_REGION };
  }

  exec_c_instr: coverpoint ins.current.insn[15:0] {
    wildcard bins c_jalr = {16'b1001_?????_?????_10};
  }

  uncompressed_jalr: coverpoint ins.prev.insn {
    wildcard bins jalr = {32'b????????????_?????_000_?????_1100111};
  }

  read_c_instr: coverpoint ins.current.insn[15:0] {
    wildcard bins c_lw   = {16'b010_???????????_00};
    wildcard bins c_lwsp = {16'b010_???????????_10};
    `ifdef XLEN64
      wildcard bins c_ld   = {16'b011_???????????_00};
      wildcard bins c_ldsp = {16'b011_???????????_10};
    `endif
    `ifdef COVER_ZCF
      wildcard bins c_flw   = {16'b011_???????????_00};
      wildcard bins c_flwsp = {16'b011_???????????_10};
    `endif
    `ifdef COVER_ZCD
      wildcard bins c_fld   = {16'b001_???????????_00};
      wildcard bins c_fldsp = {16'b001_???????????_10};
    `endif
    `ifdef COVER_ZCB
      wildcard bins c_lbu = {16'b100000_????????_00};
      wildcard bins c_lh  = {16'b100001_???1????_00};
      wildcard bins c_lhu = {16'b100001_???0????_00};
    `endif
  }

  write_c_instr: coverpoint ins.current.insn[15:0]{
    wildcard bins c_sw   = {16'b110_???????????_00};
    wildcard bins c_swsp = {16'b110_???????????_10};
    `ifdef XLEN64
      wildcard bins c_sd   = {16'b111_???????????_00};
      wildcard bins c_sdsp = {16'b111_???????????_10};
    `endif
    `ifdef COVER_ZCF
      wildcard bins c_fsw   = {16'b111_???????????_00};
      wildcard bins c_fswsp = {16'b111_???????????_10};
    `endif
    `ifdef COVER_ZCD
      wildcard bins c_fsd   = {16'b101_???????????_00};
      wildcard bins c_fsdsp = {16'b101_???????????_10};
    `endif
    `ifdef COVER_ZCB
      wildcard bins c_sb = {16'b100010_????????_00};
      wildcard bins c_sh = {16'b100011_???0????_00};
    `endif
  }

  legal_lxwr: coverpoint {pmpcfg[0],pmpcfg[1],pmpcfg[2],pmpcfg[3],pmpcfg[4],pmpcfg[5],pmp_hit[5:0]} {
    wildcard bins cfg_1000 = {54'b????????????????????????????????????????10011000_100000};
    wildcard bins cfg_1001 = {54'b????????????????????????????????10011001????????_?10000};
    wildcard bins cfg_1011 = {54'b????????????????????????10011011????????????????_??1000};
    wildcard bins cfg_1100 = {54'b????????????????10011100????????????????????????_???100};
    wildcard bins cfg_1101 = {54'b????????10011101????????????????????????????????_????10};
    wildcard bins cfg_1111 = {54'b10011111????????????????????????????????????????_?????1};
  }

  addr_in_consecutive_regions: coverpoint (ins.current.rs1_val + ins.current.imm) {
    bins inside_first_region   = {`REGIONSTART};
    bins straddle_first_second = {`REGIONSTART + `g_tor - 2};
    bins inside_second_region  = {`REGIONSTART + `g_tor};
    bins straddle_second_third = {`REGIONSTART + 2*`g_tor - 2 };
  }

  addr_in_consecutive_regions_napot: coverpoint (ins.current.rs1_val + ins.current.imm) {
    bins inside_first_region   = {`REGIONSTART};
    bins straddle_first_second = {`REGIONSTART + `g_napot - 2};
    bins inside_second_region  = {`REGIONSTART + `g_napot};
    bins straddle_second_third = {`REGIONSTART + 2*`g_napot - 2 };
  }

  `ifdef G_IS_0
    addr_in_consecutive_na4: coverpoint (ins.current.rs1_val + ins.current.imm) {
      bins straddle_first_second = {`REGIONSTART + 2};
      bins straddle_second_third = {`REGIONSTART + 6};
    }
  `endif

  addr_adjacent_to_pmp_boundary_tor: coverpoint (ins.current.rs1_val + ins.current.imm) {
    bins just_below_pmp = {`REGIONSTART - 2};          // 2 bytes before region start (possible straddle)
    bins at_start_pmp   = {`REGIONSTART};              // aligned to start of region
    bins at_end_pmp     = {`REGIONSTART + `g_tor - 2};   // 2 bytes before end → straddles out
    bins just_above_pmp = {`REGIONSTART + `g_tor};       // just outside region
  }

  addr_adjacent_to_pmp_boundary_napot: coverpoint (ins.current.rs1_val + ins.current.imm) {
    bins just_below_pmp = {`REGIONSTART - 2};          // 2 bytes before region start (possible straddle)
    bins at_start_pmp   = {`REGIONSTART};              // aligned to start of region
    bins at_end_pmp     = {`REGIONSTART + `g_napot - 2}; // 2 bytes before end → straddles out
    bins just_above_pmp = {`REGIONSTART + `g_napot};     // just outside region
  }

  `ifdef G_IS_0
    addr_adjacent_to_na4_boundary: coverpoint (ins.current.rs1_val + ins.current.imm) {
      // NA4 region (4 bytes): (REGIONSTART, REGIONSTART + 4)
      bins just_before_start     = {`REGIONSTART - 2};
      bins at_the_top     = {`REGIONSTART };
      bins at_the_bottom    = {`REGIONSTART + 2};     // 2 bytes before end → straddles out
      bins just_below = {`REGIONSTART + 4};     // just outside region
    }
  `endif

  // First three consecutive standard napot regions.
  // Region 0 -> LXWR 1111, Region 1 -> LXWR 1111, Region 2 -> LXWR 1000
  cfg_consecutive_napot: coverpoint (ins.current.csr[12'h3A0][23:0]) {
    bins locked_napot_regions = {24'b100110001001111110011111};
  }

  // First region is starting at `REGIONSTART, second region is at `REGIONSTART + `g, and third region is at `REGIONSTART + 2*`g.
  pmpaddr_consecutive_napot: coverpoint ( (pmpaddr[2] == (((`REGIONSTART+2**(`k+4)) >> 2) | (2**`k - 1)))   &&
                                          (pmpaddr[1] == (((`REGIONSTART+2**(`k+3)) >> 2) | (2**`k - 1)))   &&
                                          (pmpaddr[0] == `STANDARD_REGION)) {
    bins first_three_regions = {1};
  }

  napot_region: coverpoint (ins.current.csr[12'h3B0]) {
    bins address = {`STANDARD_REGION}; // NAPOT region with LXWR 1111
  }

  napot_setup: coverpoint (ins.current.csr[12'h3A0][7:0]) {
    bins napot_lxwr = {8'b10011111}; // NAPOT region with LXWR 1111
  }

  // First three consecutive standard tor regions.
  // Region 0 -> LXWR 1111, Region 1 -> LXWR 1111, Region 2 -> LXWR 1000
  cfg_consecutive_tor: coverpoint (ins.current.csr[12'h3A0]) {
    bins locked_tor_regions = {32'b10001000_10001111_10001111_00000000};
  }

  // PMP TOR regions configured as follows:
  // - Region 0: start at 0, end at `REGIONSTART + `g` (pmpaddr0)
  // - Region 1: start at `REGIONSTART + `g`, end at `REGIONSTART + 2*`g` (pmpaddr1)
  // - Region 2: start at `REGIONSTART + 2*`g`, end at `REGIONSTART + 3*`g` (pmpaddr2)
  pmpaddr_consecutive_tor: coverpoint ({((pmpaddr[3]) == ((`REGIONSTART + 3*`g_tor) >> 2)) &&
                                        ((pmpaddr[2]) == ((`REGIONSTART + 2*`g_tor) >> 2)) &&
                                        ((pmpaddr[1]) == ((`REGIONSTART +   `g_tor) >> 2)) &&
                                        ((pmpaddr[0]) == ((`REGIONSTART)          >> 2))}) {
    bins first_three_region = {1};
  }

  tor_region: coverpoint ({ (pmpaddr[1]==(`REGIONSTART + `g_tor)>>2) && (pmpaddr[0] == (`REGIONSTART >> 2)) }) {
    bins address = {1};
  }

  tor_setup: coverpoint (ins.current.csr[12'h3A0][15:8]) {
    bins tor_lxwr = { 8'b10001111}; // TOR region with LXWR 1111
  }

  `ifdef G_IS_0
    cfg_consecutive_na4: coverpoint (ins.current.csr[12'h3A0][23:0]) {
      bins locked_na4_regions = {24'b100100001001011110010111};
    }

    // PMP0, PMP1, PMP2: NA4, L=1, XWR=111 — regions at REGIONSTART, REGIONSTART+4, REGIONSTART+8
    pmpaddr_consecutive_na4: coverpoint ({ins.current.csr[12'h3B2], ins.current.csr[12'h3B1], ins.current.csr[12'h3B0]}) {
      bins first_three_regions = {{((`REGIONSTART + 8) >> 2), ((`REGIONSTART + 4) >> 2), (`REGIONSTART >> 2)}};
    }

    na4_region: coverpoint (ins.current.csr[12'h3B0]) {
      bins address = {`REGIONSTART >> 2}; // NA4 region with LXWR 1111
    }

    na4_setup: coverpoint (ins.current.csr[12'h3A0][7:0]) {
      bins na4_lxwr = { 8'b10010111}; // NA4 region with LXWR 1111
    }

  `endif

  cfg_consecutive_off: coverpoint (ins.current.csr[12'h3A0][23:0]) {
    bins locked_off_regions = {24'b100001111000011110000111};
  }

  cp_cfg_R: cross priv_mode_m, legal_lxwr, addr_in_region, read_c_instr {
    ignore_bins ig1 = binsof(addr_in_region.at_region) && binsof(read_c_instr.c_lwsp);
    `ifdef XLEN64
      ignore_bins ig2 = binsof(addr_in_region.at_region) && binsof(read_c_instr.c_ldsp);
    `endif
  }
  cp_cfg_W: cross priv_mode_m, legal_lxwr, addr_in_region, write_c_instr;

  cp_misaligned_napot: cross priv_mode_m, cfg_consecutive_napot, pmpaddr_consecutive_napot, addr_in_consecutive_regions, exec_c_instr;
  cp_cret_napot: cross priv_mode_m, napot_setup, napot_region, exec_c_instr, addr_adjacent_to_pmp_boundary_napot;

  cp_misaligned_tor: cross priv_mode_m, cfg_consecutive_tor, pmpaddr_consecutive_tor, addr_in_consecutive_regions, exec_c_instr;
  cp_cret_tor: cross priv_mode_m, tor_setup, tor_region, exec_c_instr, addr_adjacent_to_pmp_boundary_tor;

  `ifdef G_IS_0
    cp_misaligned_na4: cross priv_mode_m, cfg_consecutive_na4, pmpaddr_consecutive_na4, addr_in_consecutive_na4, exec_c_instr;
    cp_cret_na4: cross priv_mode_m, na4_setup, na4_region, exec_c_instr, addr_adjacent_to_na4_boundary;
  `endif

  cp_misaligned_off: cross priv_mode_m, cfg_consecutive_off, addr_in_consecutive_regions, exec_c_instr;

endgroup

function void pmpzca_sample(int hart, int issue, ins_t ins);

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

  PMPZca_cg.sample(ins, pmpcfg, pmp_hit, pmpaddr);
endfunction
