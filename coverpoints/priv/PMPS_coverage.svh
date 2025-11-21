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

covergroup PMPS_cg with function sample(ins_t ins, logic [16*XLEN-1:0] pack_pmpaddr, logic [29:0] pmpcfg_a, [7:0] pmpcfg [63:0], logic [14:0] pmp_hit);
  option.per_instance = 0;
  `include  "general/RISCV_coverage_standard_coverpoints.svh"

  addr_in_region: coverpoint (ins.current.rs1_val + ins.current.imm) {
    bins at_region = {`REGIONSTART};
  }

  addr_offset_napot: coverpoint (ins.current.rs1_val + ins.current.imm) {
    bins at_base      = {`REGIONSTART};                // Access exactly at the region base
    bins below_base   = {`REGIONSTART - 4};            // Access 4 bytes below the region
    bins just_inside  = {`REGIONSTART + 4};            // Access 4 bytes into the region
    bins highest_word = {`REGIONSTART + `g_napot - 4}; // Access at the last word in region
    bins just_beyond  = {`REGIONSTART + `g_napot};     // Access exactly at the end of the region
  }

  addr_offset_na4: coverpoint (ins.current.rs1_val + ins.current.imm) {
    bins at_base     = {`REGIONSTART};      // Access exactly at the region base
    bins below_base  = {`REGIONSTART - 4};  // Access below region base
    bins beyond_top  = {`REGIONSTART + 4};  // Access beyond top of region
  }

  // if range is from `REGIONSTART to `REGIONSTART + `g
  addr_offset_tor: coverpoint (ins.current.rs1_val + ins.current.imm) {
    bins at_base      = {`REGIONSTART};              // Access exactly at the region base
    bins below_base   = {`REGIONSTART - 4};          // Access 4 bytes below the base
    bins at_top       = {`REGIONSTART + `g_tor};     // Access exactly at top of range
    bins highest_word = {`REGIONSTART + `g_tor - 4}; // Access at the last word in region
  }

  exec_instr: coverpoint ins.current.insn {
    wildcard bins jalr = {32'b????????????_?????_000_?????_1100111};
  }

  read_instr: coverpoint ins.current.insn {
    wildcard bins lb  = {32'b????????????_?????_000_?????_0000011};
    wildcard bins lbu = {32'b????????????_?????_100_?????_0000011};
    wildcard bins lh  = {32'b????????????_?????_001_?????_0000011};
    wildcard bins lhu = {32'b????????????_?????_101_?????_0000011};
    wildcard bins lw  = {32'b????????????_?????_010_?????_0000011};
    `ifdef XLEN64
      wildcard bins lwu = {32'b????????????_?????_110_?????_0000011};
      wildcard bins ld  = {32'b????????????_?????_011_?????_0000011};
    `endif
  }
  read_instr_lw: coverpoint ins.current.insn {
    wildcard bins lw  = {32'b????????????_?????_010_?????_0000011};
  }

  write_instr: coverpoint ins.current.insn {
    wildcard bins sb = {32'b???????_?????_?????_000_?????_0100011};
    wildcard bins sh = {32'b???????_?????_?????_001_?????_0100011};
    wildcard bins sw = {32'b???????_?????_?????_010_?????_0100011};
    `ifdef XLEN64
      wildcard bins sd = {32'b???????_?????_?????_011_?????_0100011};
    `endif
  }

  write_instr_sw: coverpoint ins.current.insn {
    wildcard bins sw = {32'b???????_?????_?????_010_?????_0100011};
  }

//-------------------------------------------------------

  standard_region: coverpoint ins.current.csr[12'h3B0] {
    bins standard_region = {`STANDARD_REGION};
  }

  legal_lxwr: coverpoint {pmpcfg[0],pmpcfg[1],pmpcfg[2],pmpcfg[3],pmpcfg[4],pmpcfg[5],pmp_hit[5:0]} {
    wildcard bins cfg_1000 = {54'b????????????????????????????????????????10011000_100000};
    wildcard bins cfg_1001 = {54'b????????????????????????????????10011001????????_?10000};
    wildcard bins cfg_1011 = {54'b????????????????????????10011011????????????????_??1000};
    wildcard bins cfg_1100 = {54'b????????????????10011100????????????????????????_???100};
    wildcard bins cfg_1101 = {54'b????????10011101????????????????????????????????_????10};
    wildcard bins cfg_1111 = {54'b10011111????????????????????????????????????????_?????1};
    wildcard bins cfg_0000 = {54'b????????????????????????????????????????00011000_100000};
    wildcard bins cfg_0001 = {54'b????????????????????????????????00011001????????_?10000};
    wildcard bins cfg_0011 = {54'b????????????????????????00011011????????????????_??1000};
    wildcard bins cfg_0100 = {54'b????????????????00011100????????????????????????_???100};
    wildcard bins cfg_0101 = {54'b????????00011101????????????????????????????????_????10};
    wildcard bins cfg_0111 = {54'b00011111????????????????????????????????????????_?????1};
  }

  all_pmp_entries_off: coverpoint pmpcfg_a { // Including Background Top PMP Entry
    bins PMP_OFF = {0};
  }

  // pack_pmpaddr has all the pmpaddr csrs, so when it's zero implies all pmpaddr = 0
  all_pmpaddr_zero: coverpoint pack_pmpaddr { // Including Background Top PMP Entry
    bins pmpaddr_zeros = {0};
  }

  pmpaddr_entries: coverpoint ins.current.insn[31:20] {
    bins pmpaddr0   = {12'h3B0};
    bins pmpaddr1   = {12'h3B1};
    bins pmpaddr2   = {12'h3B2};
    bins pmpaddr3   = {12'h3B3};
    bins pmpaddr4   = {12'h3B4};
    bins pmpaddr5   = {12'h3B5};
    bins pmpaddr6   = {12'h3B6};
    bins pmpaddr7   = {12'h3B7};
    bins pmpaddr8   = {12'h3B8};
    bins pmpaddr9   = {12'h3B9};
    bins pmpaddr10  = {12'h3BA};
    bins pmpaddr11  = {12'h3BB};
    bins pmpaddr12  = {12'h3BC};
    bins pmpaddr13  = {12'h3BD};
    bins pmpaddr14  = {12'h3BE};
    bins pmpaddr15  = {12'h3BF};
    bins pmpaddr16  = {12'h3C0};
    bins pmpaddr17  = {12'h3C1};
    bins pmpaddr18  = {12'h3C2};
    bins pmpaddr19  = {12'h3C3};
    bins pmpaddr20  = {12'h3C4};
    bins pmpaddr21  = {12'h3C5};
    bins pmpaddr22  = {12'h3C6};
    bins pmpaddr23  = {12'h3C7};
    bins pmpaddr24  = {12'h3C8};
    bins pmpaddr25  = {12'h3C9};
    bins pmpaddr26  = {12'h3CA};
    bins pmpaddr27  = {12'h3CB};
    bins pmpaddr28  = {12'h3CC};
    bins pmpaddr29  = {12'h3CD};
    bins pmpaddr30  = {12'h3CE};
    bins pmpaddr31  = {12'h3CF};
    bins pmpaddr32  = {12'h3D0};
    bins pmpaddr33  = {12'h3D1};
    bins pmpaddr34  = {12'h3D2};
    bins pmpaddr35  = {12'h3D3};
    bins pmpaddr36  = {12'h3D4};
    bins pmpaddr37  = {12'h3D5};
    bins pmpaddr38  = {12'h3D6};
    bins pmpaddr39  = {12'h3D7};
    bins pmpaddr40  = {12'h3D8};
    bins pmpaddr41  = {12'h3D9};
    bins pmpaddr42  = {12'h3DA};
    bins pmpaddr43  = {12'h3DB};
    bins pmpaddr44  = {12'h3DC};
    bins pmpaddr45  = {12'h3DD};
    bins pmpaddr46  = {12'h3DE};
    bins pmpaddr47  = {12'h3DF};
    bins pmpaddr48  = {12'h3E0};
    bins pmpaddr49  = {12'h3E1};
    bins pmpaddr50  = {12'h3E2};
    bins pmpaddr51  = {12'h3E3};
    bins pmpaddr52  = {12'h3E4};
    bins pmpaddr53  = {12'h3E5};
    bins pmpaddr54  = {12'h3E6};
    bins pmpaddr55  = {12'h3E7};
    bins pmpaddr56  = {12'h3E8};
    bins pmpaddr57  = {12'h3E9};
    bins pmpaddr58  = {12'h3EA};
    bins pmpaddr59  = {12'h3EB};
    bins pmpaddr60  = {12'h3EC};
    bins pmpaddr61  = {12'h3ED};
    bins pmpaddr62  = {12'h3EE};
    bins pmpaddr63  = {12'h3EF};
  }

  pmpcfg_entries: coverpoint ins.current.insn[31:20] {
    bins pmpcfg0   = {12'h3A0};
    bins pmpcfg1   = {12'h3A1};
    bins pmpcfg2   = {12'h3A2};
    bins pmpcfg3   = {12'h3A3};
    bins pmpcfg4   = {12'h3A4};
    bins pmpcfg5   = {12'h3A5};
    bins pmpcfg6   = {12'h3A6};
    bins pmpcfg7   = {12'h3A7};
    bins pmpcfg8   = {12'h3A8};
    bins pmpcfg9   = {12'h3A9};
    bins pmpcfg10  = {12'h3AA};
    bins pmpcfg11  = {12'h3AB};
    bins pmpcfg12  = {12'h3AC};
    bins pmpcfg13  = {12'h3AD};
    bins pmpcfg14  = {12'h3AE};
    bins pmpcfg15  = {12'h3AF};
  }

  mode_switch: coverpoint ins.current.insn {
    bins mret = {32'b00110000001000000000000001110011};
  }

  csrrw: coverpoint ins.current.insn {
    wildcard bins csrrw  = {32'b????????????_?????_001_?????_1110011};
  }

  mprv_mstatus: coverpoint ins.prev.csr[12'h300][17]{
    bins set   = {1};
    bins unset = {0};
  }

  mpp_mstatus: coverpoint ins.prev.csr[12'h300][12:11] {
    bins S_mode = {2'b01};
  }

  lxwr: coverpoint ins.current.csr[12'h3A0][7:0] {
    bins cfg_1000 = {8'b10011000};
    bins cfg_1111 = {8'b10011111};
    bins cfg_0000 = {8'b00011000};
    bins cfg_0111 = {8'b00011111};
  }

  // pmpcfg_i.L = 0, pmpcfg_i.A = OFF, pmpcfg_i.XWR = 000, pmpaddr_i = all 1s
  cfg_A_off: coverpoint {ins.current.csr[12'h3A0][7:0],ins.current.csr[12'h3B0]} {
    bins region_off = {8'b00000000,{$bits(ins.current.csr[12'h3B0][`EFFECTIVE_PMPADDR:0]){1'b1}}};
  }

  // pmpcfg_i.L = 0, pmpcfg_i.A = NAPOT, all legal pmpcfg_i.XWR, pmpaddr_i = `STANDARD_REGION
  cfg_A_napot: coverpoint {pmpcfg[0],pmpcfg[1],pmpcfg[2],pmpcfg[3],pmpcfg[4],pmpcfg[5],pmp_hit[5:0]} {
    wildcard bins napot_lwxr_0000 = {54'b????????????????????????????????????????00011000_100000};
    wildcard bins napot_lwxr_0001 = {54'b????????????????????????????????00011001????????_?10000};
    wildcard bins napot_lwxr_0011 = {54'b????????????????????????00011011????????????????_??1000};
    wildcard bins napot_lwxr_0100 = {54'b????????????????00011100????????????????????????_???100};
    wildcard bins napot_lwxr_0101 = {54'b????????00011101????????????????????????????????_????10};
    wildcard bins napot_lwxr_0111 = {54'b00011111????????????????????????????????????????_?????1};
  }

  `ifdef G_IS_0
    // pmpcfg_i.L = 0, pmpcfg_i.A = NA4, all legal pmpcfg_i.XWR, pmpaddr_i = `NON_STANDARD_REGION
    cfg_A_na4: coverpoint {pmpcfg[0],pmpcfg[1],pmpcfg[2],pmpcfg[3],pmpcfg[4],pmpcfg[5],pmp_hit[5:0]} {
      wildcard bins na4_lwxr_0000 = {54'b????????????????????????????????????????00010000_100000};
      wildcard bins na4_lwxr_0001 = {54'b????????????????????????????????00010001????????_?10000};
      wildcard bins na4_lwxr_0011 = {54'b????????????????????????00010011????????????????_??1000};
      wildcard bins na4_lwxr_0100 = {54'b????????????????00010100????????????????????????_???100};
      wildcard bins na4_lwxr_0101 = {54'b????????00010101????????????????????????????????_????10};
      wildcard bins na4_lwxr_0111 = {54'b00010111????????????????????????????????????????_?????1};
    }
  `endif

  // pmpcfg_i.L = 0, pmpcfg_i.A = TOR, all legal pmpcfg_i.XWR, pmpaddr_i = `NON_STANDARD_REGION + `g, pmpaddr_i-1 = `NON_STANDARD_REGION
  cfg_A_tor: coverpoint {pmpcfg[1],pmpcfg[3],pmpcfg[5],pmpcfg[7],pmpcfg[9],pmpcfg[11],pmp_hit[11:0]} {
    wildcard bins tor_lwxr_0000 = {60'b????????????????????????????????????????00001000_?10000000000};
    wildcard bins tor_lwxr_0001 = {60'b????????????????????????????????00001001????????_???100000000};
    wildcard bins tor_lwxr_0011 = {60'b????????????????????????00001011????????????????_?????1000000};
    wildcard bins tor_lwxr_0100 = {60'b????????????????00001100????????????????????????_???????10000};
    wildcard bins tor_lwxr_0101 = {60'b????????00001101????????????????????????????????_?????????100};
    wildcard bins tor_lwxr_0111 = {60'b00001111????????????????????????????????????????_???????????1};
  }

//-------------------------------------------------------

  cp_cfg_X: cross priv_mode_s, legal_lxwr, exec_instr, addr_in_region ;
  cp_cfg_R: cross priv_mode_s, legal_lxwr, read_instr, addr_in_region ;
  cp_cfg_W: cross priv_mode_s, legal_lxwr, write_instr, addr_in_region ;

  cp_none: cross priv_mode_m, mpp_mstatus, all_pmp_entries_off, all_pmpaddr_zero, mode_switch ;

  cp_cfg_A_off_jalr: cross priv_mode_s, cfg_A_off, exec_instr, addr_in_region ;
  cp_cfg_A_off_lw: cross priv_mode_s, cfg_A_off, read_instr_lw, addr_in_region ;
  cp_cfg_A_off_sw: cross priv_mode_s, cfg_A_off, write_instr_sw, addr_in_region ;

  // Access at start of region, start - 4, start + 4, highest word in region, just beyond top of the region
  cp_cfg_A_napot_jalr: cross priv_mode_s, cfg_A_napot, exec_instr, addr_offset_napot ;
  cp_cfg_A_napot_lw: cross priv_mode_s, cfg_A_napot, read_instr_lw, addr_offset_napot ;
  cp_cfg_A_napot_sw: cross priv_mode_s, cfg_A_napot, write_instr_sw, addr_offset_napot ;

  `ifdef G_IS_0
    // Access at start of address, that address - 4, just beyond top of the region.
    cp_cfg_A_na4_jalr: cross priv_mode_s, cfg_A_na4, exec_instr, addr_offset_na4 ;
    cp_cfg_A_na4_lw: cross priv_mode_s, cfg_A_na4, read_instr_lw, addr_offset_na4 ;
    cp_cfg_A_na4_sw: cross priv_mode_s, cfg_A_na4, write_instr_sw, addr_offset_na4 ;
  `endif

  // Access at address, address-4, address-g, address-g-4.
  cp_cfg_A_tor_jalr: cross priv_mode_s, cfg_A_tor, exec_instr, addr_offset_tor ;
  cp_cfg_A_tor_lw: cross priv_mode_s, cfg_A_tor, read_instr_lw, addr_offset_tor ;
  cp_cfg_A_tor_sw: cross priv_mode_s, cfg_A_tor, write_instr_sw, addr_offset_tor ;

  cp_mprv_jalr: cross priv_mode_m, mprv_mstatus, mpp_mstatus, lxwr, exec_instr, standard_region, addr_in_region ;
  cp_mprv_lw: cross priv_mode_m, mprv_mstatus, mpp_mstatus, lxwr, read_instr_lw, standard_region, addr_in_region ;
  cp_mprv_sw: cross priv_mode_m, mprv_mstatus, mpp_mstatus, lxwr, write_instr_sw, standard_region, addr_in_region ;

  cp_pmpaddr_access_s: cross priv_mode_s, csrrw, pmpaddr_entries ;
  cp_pmpcfg_access_s: cross priv_mode_s, csrrw, pmpcfg_entries ;

endgroup

function void pmps_sample(int hart, int issue, ins_t ins);

  logic [16*XLEN-1:0] pack_pmpaddr;
  logic [29:0] pmpcfg_a;      // for first 15 Regions
  logic [7:0] pmpcfg [63:0];
  logic [XLEN-1:0] pmpaddr [62:0];
  logic [14:0] pmp_hit;

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

  pack_pmpaddr = { ins.current.csr[12'h3BF]
                  ,ins.current.csr[12'h3BE]
                  ,ins.current.csr[12'h3BD]
                  ,ins.current.csr[12'h3BC]
                  ,ins.current.csr[12'h3BB]
                  ,ins.current.csr[12'h3BA]
                  ,ins.current.csr[12'h3B9]
                  ,ins.current.csr[12'h3B8]
                  ,ins.current.csr[12'h3B7]
                  ,ins.current.csr[12'h3B6]
                  ,ins.current.csr[12'h3B5]
                  ,ins.current.csr[12'h3B4]
                  ,ins.current.csr[12'h3B3]
                  ,ins.current.csr[12'h3B2]
                  ,ins.current.csr[12'h3B1]
                  ,ins.current.csr[12'h3B0]
                };

  `ifdef XLEN32
    pmpcfg_a =  {
          ins.current.csr[12'h3A3][28:27],
          ins.current.csr[12'h3A3][20:19],
          ins.current.csr[12'h3A3][12:11],
          ins.current.csr[12'h3A3][4:3],
          ins.current.csr[12'h3A2][28:27],
          ins.current.csr[12'h3A2][20:19],
          ins.current.csr[12'h3A2][12:11],
          ins.current.csr[12'h3A2][4:3],
          ins.current.csr[12'h3A1][28:27],
          ins.current.csr[12'h3A1][20:19],
          ins.current.csr[12'h3A1][12:11],
          ins.current.csr[12'h3A1][4:3],
          ins.current.csr[12'h3A0][28:27],
          ins.current.csr[12'h3A0][20:19],
          ins.current.csr[12'h3A0][12:11],
          ins.current.csr[12'h3A0][4:3]
          };
  `endif
  `ifdef XLEN64
    pmpcfg_a =  {
          ins.current.csr[12'h3A2][60:59],
          ins.current.csr[12'h3A2][52:51],
          ins.current.csr[12'h3A2][44:43],
          ins.current.csr[12'h3A2][36:35],
          ins.current.csr[12'h3A2][28:27],
          ins.current.csr[12'h3A2][20:19],
          ins.current.csr[12'h3A2][12:11],
          ins.current.csr[12'h3A2][4:3],
          ins.current.csr[12'h3A0][60:59],
          ins.current.csr[12'h3A0][52:51],
          ins.current.csr[12'h3A0][44:43],
          ins.current.csr[12'h3A0][36:35],
          ins.current.csr[12'h3A0][28:27],
          ins.current.csr[12'h3A0][20:19],
          ins.current.csr[12'h3A0][12:11],
          ins.current.csr[12'h3A0][4:3]
          };
  `endif
  PMPS_cg.sample(ins, pack_pmpaddr, pmpcfg_a, pmpcfg, pmp_hit);
endfunction
