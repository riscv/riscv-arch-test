///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Standard Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_PMPS

covergroup PMPS_cg with function sample(ins_t ins, logic [16*XLEN-1:0] pack_pmpaddr, logic [29:0] pmpcfg_a, [7:0] pmpcfg [63:0], logic [14:0] pmp_hit);
  option.per_instance = 0;
  `include  "general/RISCV_coverage_standard_coverpoints.svh"

  addr_in_region: coverpoint (ins.current.rs1_val + ins.current.imm) {
    bins at_region = {`PMP_REGION_START};
  }

  addr_offset_napot: coverpoint (ins.current.rs1_val + ins.current.imm) {
    bins at_base      = {`PMP_REGION_START};                // Access exactly at the region base
    bins below_base   = {`PMP_REGION_START - 4};            // Access 4 bytes below the region
    bins just_inside  = {`PMP_REGION_START + 4};            // Access 4 bytes into the region
    bins highest_word = {`PMP_REGION_START + `g_napot - 4}; // Access at the last word in region
    bins just_beyond  = {`PMP_REGION_START + `g_napot};     // Access exactly at the end of the region
  }

  addr_offset_na4: coverpoint (ins.current.rs1_val + ins.current.imm) {
    bins at_base     = {`PMP_REGION_START};      // Access exactly at the region base
    bins below_base  = {`PMP_REGION_START - 4};  // Access below region base
    bins beyond_top  = {`PMP_REGION_START + 4};  // Access beyond top of region
  }

  // if range is from `PMP_REGION_START to `PMP_REGION_START + `g
  addr_offset_tor: coverpoint (ins.current.rs1_val + ins.current.imm) {
    bins at_base      = {`PMP_REGION_START};              // Access exactly at the region base
    bins below_base   = {`PMP_REGION_START - 4};          // Access 4 bytes below the base
    bins at_top       = {`PMP_REGION_START + `g_tor};     // Access exactly at top of range
    bins highest_word = {`PMP_REGION_START + `g_tor - 4}; // Access at the last word in region
  }

  exec_instr: coverpoint ins.current.insn {
    wildcard bins jalr = {JALR};
  }

  read_instr: coverpoint ins.current.insn {
    wildcard bins lb  = {LB};
    wildcard bins lbu = {LBU};
    wildcard bins lh  = {LH};
    wildcard bins lhu = {LHU};
    wildcard bins lw  = {LW};
    `ifdef XLEN64
      wildcard bins lwu = {LWU};
      wildcard bins ld  = {LD};
    `endif
  }
  read_instr_lw: coverpoint ins.current.insn {
    wildcard bins lw  = {LW};
  }

  write_instr: coverpoint ins.current.insn {
    wildcard bins sb = {SB};
    wildcard bins sh = {SH};
    wildcard bins sw = {SW};
    `ifdef XLEN64
      wildcard bins sd = {SD};
    `endif
  }

  write_instr_sw: coverpoint ins.current.insn {
    wildcard bins sw = {SW};
  }

//-------------------------------------------------------

  standard_region: coverpoint ins.current.csr[CSR_PMPADDR0] {
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


  pmpaddr_entries: coverpoint ins.current.insn[31:20] {
    bins pmpaddr0   = {CSR_PMPADDR0};
    bins pmpaddr1   = {CSR_PMPADDR1};
    bins pmpaddr2   = {CSR_PMPADDR2};
    bins pmpaddr3   = {CSR_PMPADDR3};
    bins pmpaddr4   = {CSR_PMPADDR4};
    bins pmpaddr5   = {CSR_PMPADDR5};
    bins pmpaddr6   = {CSR_PMPADDR6};
    bins pmpaddr7   = {CSR_PMPADDR7};
    bins pmpaddr8   = {CSR_PMPADDR8};
    bins pmpaddr9   = {CSR_PMPADDR9};
    bins pmpaddr10  = {CSR_PMPADDR10};
    bins pmpaddr11  = {CSR_PMPADDR11};
    bins pmpaddr12  = {CSR_PMPADDR12};
    bins pmpaddr13  = {CSR_PMPADDR13};
    bins pmpaddr14  = {CSR_PMPADDR14};
    bins pmpaddr15  = {CSR_PMPADDR15};
    bins pmpaddr16  = {CSR_PMPADDR16};
    bins pmpaddr17  = {CSR_PMPADDR17};
    bins pmpaddr18  = {CSR_PMPADDR18};
    bins pmpaddr19  = {CSR_PMPADDR19};
    bins pmpaddr20  = {CSR_PMPADDR20};
    bins pmpaddr21  = {CSR_PMPADDR21};
    bins pmpaddr22  = {CSR_PMPADDR22};
    bins pmpaddr23  = {CSR_PMPADDR23};
    bins pmpaddr24  = {CSR_PMPADDR24};
    bins pmpaddr25  = {CSR_PMPADDR25};
    bins pmpaddr26  = {CSR_PMPADDR26};
    bins pmpaddr27  = {CSR_PMPADDR27};
    bins pmpaddr28  = {CSR_PMPADDR28};
    bins pmpaddr29  = {CSR_PMPADDR29};
    bins pmpaddr30  = {CSR_PMPADDR30};
    bins pmpaddr31  = {CSR_PMPADDR31};
    bins pmpaddr32  = {CSR_PMPADDR32};
    bins pmpaddr33  = {CSR_PMPADDR33};
    bins pmpaddr34  = {CSR_PMPADDR34};
    bins pmpaddr35  = {CSR_PMPADDR35};
    bins pmpaddr36  = {CSR_PMPADDR36};
    bins pmpaddr37  = {CSR_PMPADDR37};
    bins pmpaddr38  = {CSR_PMPADDR38};
    bins pmpaddr39  = {CSR_PMPADDR39};
    bins pmpaddr40  = {CSR_PMPADDR40};
    bins pmpaddr41  = {CSR_PMPADDR41};
    bins pmpaddr42  = {CSR_PMPADDR42};
    bins pmpaddr43  = {CSR_PMPADDR43};
    bins pmpaddr44  = {CSR_PMPADDR44};
    bins pmpaddr45  = {CSR_PMPADDR45};
    bins pmpaddr46  = {CSR_PMPADDR46};
    bins pmpaddr47  = {CSR_PMPADDR47};
    bins pmpaddr48  = {CSR_PMPADDR48};
    bins pmpaddr49  = {CSR_PMPADDR49};
    bins pmpaddr50  = {CSR_PMPADDR50};
    bins pmpaddr51  = {CSR_PMPADDR51};
    bins pmpaddr52  = {CSR_PMPADDR52};
    bins pmpaddr53  = {CSR_PMPADDR53};
    bins pmpaddr54  = {CSR_PMPADDR54};
    bins pmpaddr55  = {CSR_PMPADDR55};
    bins pmpaddr56  = {CSR_PMPADDR56};
    bins pmpaddr57  = {CSR_PMPADDR57};
    bins pmpaddr58  = {CSR_PMPADDR58};
    bins pmpaddr59  = {CSR_PMPADDR59};
    bins pmpaddr60  = {CSR_PMPADDR60};
    bins pmpaddr61  = {CSR_PMPADDR61};
    bins pmpaddr62  = {CSR_PMPADDR62};
    bins pmpaddr63  = {CSR_PMPADDR63};
  }

  pmpcfg_entries: coverpoint ins.current.insn[31:20] {
    bins pmpcfg0   = {CSR_PMPCFG0};
    bins pmpcfg1   = {CSR_PMPCFG1};
    bins pmpcfg2   = {CSR_PMPCFG2};
    bins pmpcfg3   = {CSR_PMPCFG3};
    bins pmpcfg4   = {CSR_PMPCFG4};
    bins pmpcfg5   = {CSR_PMPCFG5};
    bins pmpcfg6   = {CSR_PMPCFG6};
    bins pmpcfg7   = {CSR_PMPCFG7};
    bins pmpcfg8   = {CSR_PMPCFG8};
    bins pmpcfg9   = {CSR_PMPCFG9};
    bins pmpcfg10  = {CSR_PMPCFG10};
    bins pmpcfg11  = {CSR_PMPCFG11};
    bins pmpcfg12  = {CSR_PMPCFG12};
    bins pmpcfg13  = {CSR_PMPCFG13};
    bins pmpcfg14  = {CSR_PMPCFG14};
    bins pmpcfg15  = {CSR_PMPCFG15};
  }

<<<<<<< act4-work
=======
  mode_switch: coverpoint ins.current.insn {
    bins mret = {MRET};
  }

>>>>>>> act4
  csrrw: coverpoint ins.current.insn {
    wildcard bins csrrw  = {CSRRW};
  }

  mprv_mstatus: coverpoint ins.prev.csr[CSR_MSTATUS][17]{
    bins set   = {1};
    bins unset = {0};
  }

  mpp_mstatus: coverpoint ins.prev.csr[CSR_MSTATUS][12:11] {
    bins S_mode = {2'b01};
  }

  lxwr: coverpoint ins.current.csr[CSR_PMPCFG0][7:0] {
    bins cfg_1000 = {8'b10011000};
    bins cfg_1111 = {8'b10011111};
    bins cfg_0000 = {8'b00011000};
    bins cfg_0111 = {8'b00011111};
  }

  // pmpcfg_i.L = 0, pmpcfg_i.A = OFF, pmpcfg_i.XWR = 000, pmpaddr_i = all 1s
  cfg_A_off: coverpoint {ins.current.csr[CSR_PMPCFG0][7:0],ins.current.csr[CSR_PMPADDR0]} {
    bins region_off = {8'b00000000,{$bits(ins.current.csr[CSR_PMPADDR0][`EFFECTIVE_PMPADDR:0]){1'b1}}};
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
      logic [31:0] cfg_word = ins.current.csr[CSR_PMPCFG0 + i];
      pmpcfg[i*4 + 0] = cfg_word[7:0];
      pmpcfg[i*4 + 1] = cfg_word[15:8];
      pmpcfg[i*4 + 2] = cfg_word[23:16];
      pmpcfg[i*4 + 3] = cfg_word[31:24];
    end
  `elsif XLEN64
    // Each pmpcfg CSR holds 8 region configs in 64-bit (8x 8-bit)
    for (int i = 0; i < 8; i++) begin
      logic [63:0] cfg_word = ins.current.csr[CSR_PMPCFG0 + 2*i];
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
    pmpaddr[j] = ins.current.csr[CSR_PMPADDR0 + j];
  end

  for (int k = 0; k < 15; k++) begin  // Check for first 15 PMP regions
    pmp_hit[k] = (pmpaddr[k] == `STANDARD_REGION) || (pmpaddr[k] == `NON_STANDARD_REGION);
  end

  pack_pmpaddr = { ins.current.csr[CSR_PMPADDR15]
                  ,ins.current.csr[CSR_PMPADDR14]
                  ,ins.current.csr[CSR_PMPADDR13]
                  ,ins.current.csr[CSR_PMPADDR12]
                  ,ins.current.csr[CSR_PMPADDR11]
                  ,ins.current.csr[CSR_PMPADDR10]
                  ,ins.current.csr[CSR_PMPADDR9]
                  ,ins.current.csr[CSR_PMPADDR8]
                  ,ins.current.csr[CSR_PMPADDR7]
                  ,ins.current.csr[CSR_PMPADDR6]
                  ,ins.current.csr[CSR_PMPADDR5]
                  ,ins.current.csr[CSR_PMPADDR4]
                  ,ins.current.csr[CSR_PMPADDR3]
                  ,ins.current.csr[CSR_PMPADDR2]
                  ,ins.current.csr[CSR_PMPADDR1]
                  ,ins.current.csr[CSR_PMPADDR0]
                };

  `ifdef XLEN32
    pmpcfg_a =  {
          ins.current.csr[CSR_PMPCFG3][28:27],
          ins.current.csr[CSR_PMPCFG3][20:19],
          ins.current.csr[CSR_PMPCFG3][12:11],
          ins.current.csr[CSR_PMPCFG3][4:3],
          ins.current.csr[CSR_PMPCFG2][28:27],
          ins.current.csr[CSR_PMPCFG2][20:19],
          ins.current.csr[CSR_PMPCFG2][12:11],
          ins.current.csr[CSR_PMPCFG2][4:3],
          ins.current.csr[CSR_PMPCFG1][28:27],
          ins.current.csr[CSR_PMPCFG1][20:19],
          ins.current.csr[CSR_PMPCFG1][12:11],
          ins.current.csr[CSR_PMPCFG1][4:3],
          ins.current.csr[CSR_PMPCFG0][28:27],
          ins.current.csr[CSR_PMPCFG0][20:19],
          ins.current.csr[CSR_PMPCFG0][12:11],
          ins.current.csr[CSR_PMPCFG0][4:3]
          };
  `endif
  `ifdef XLEN64
    pmpcfg_a =  {
          ins.current.csr[CSR_PMPCFG2][60:59],
          ins.current.csr[CSR_PMPCFG2][52:51],
          ins.current.csr[CSR_PMPCFG2][44:43],
          ins.current.csr[CSR_PMPCFG2][36:35],
          ins.current.csr[CSR_PMPCFG2][28:27],
          ins.current.csr[CSR_PMPCFG2][20:19],
          ins.current.csr[CSR_PMPCFG2][12:11],
          ins.current.csr[CSR_PMPCFG2][4:3],
          ins.current.csr[CSR_PMPCFG0][60:59],
          ins.current.csr[CSR_PMPCFG0][52:51],
          ins.current.csr[CSR_PMPCFG0][44:43],
          ins.current.csr[CSR_PMPCFG0][36:35],
          ins.current.csr[CSR_PMPCFG0][28:27],
          ins.current.csr[CSR_PMPCFG0][20:19],
          ins.current.csr[CSR_PMPCFG0][12:11],
          ins.current.csr[CSR_PMPCFG0][4:3]
          };
  `endif
  PMPS_cg.sample(ins, pack_pmpaddr, pmpcfg_a, pmpcfg, pmp_hit);
endfunction
