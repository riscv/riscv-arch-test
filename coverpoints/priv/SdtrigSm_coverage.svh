///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Angela Zheng, angela20061015@gmail.com, 10 September 2026
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`define COVER_SDTRIGSM

covergroup SdtrigSm_trig_module_reg_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"

    type_disabled: coverpoint ins.current.csr[CSR_TDATA1][XLEN-1:XLEN-4] {
        bins disabled = {4'd15};
    }
    tdata1_type_six: coverpoint ins.current.rs1_val[XLEN-1:XLEN-4] {
        bins mcontrol6 = {4'd6};
    }
    priv_bits: coverpoint ins.current.rs1_val[26:0] {
        bins priv = {27'b001_1000_0000_0000_0000_0101_1000};
    }
    csr_tselect:  coverpoint ins.current.insn[31:20] {
        bins tselect = {CSR_TSELECT};
    }
    csr_tdata: coverpoint ins.current.insn[31:20] {
        bins tdata1 = {CSR_TDATA1};
        bins tdata2 = {CSR_TDATA2};
        bins tdata3 = {CSR_TDATA3};
    }
    csr_tdata1: coverpoint ins.current.insn[31:20] {
        bins tdata1 = {CSR_TDATA1};
    }
    csr_tinfo: coverpoint ins.current.insn[31:20] {
        bins tinfo = {CSR_TINFO};
    }
    csr_global_reg: coverpoint ins.current.insn[31:20] {
        bins tselect  = {CSR_TSELECT};
        bins tcontrol = {CSR_TCONTROL};
        bins mcontext = {CSR_MCONTEXT};
        bins scontext = {CSR_SCONTEXT};
        `ifdef H_SUPPORTED
            bins hcontext = {CSR_HCONTEXT};
        `endif
    }
    csr_local_reg: coverpoint ins.current.insn[31:20] {
        bins tdata1 = {CSR_TDATA1};
        bins tdata2 = {CSR_TDATA2};
        bins tdata3 = {CSR_TDATA3};
        bins tinfo  = {CSR_TINFO};
    }
    csr_access: coverpoint ins.current.insn{
        wildcard bins csrrw0 = {CSRRW} iff (ins.current.rs1_val == '0);
        wildcard bins csrrw1 = {CSRRW} iff (ins.current.rs1_val == '1);
    }

    // main coverpoints
    cp_tdata_write:           cross priv_mode_m, triggernum, type_disabled, csr_tdata, csr_access;          // NTRIG * 3 CSRs * 2 values
    cp_csr_access_global:     cross priv_mode_m, csr_global_reg, csr_access;                                // 5 CSRs * 2 values
    cp_csr_access_local:      cross priv_mode_m, triggernum, csr_local_reg, csr_access;                     // NTRIG * 4 CSRs * 2 values
    cp_tselect_trigs:         cross priv_mode_m, triggernum, csrr, csr_tselect;                             // NTRIG
    cp_tdata1_mode_hardwired: cross priv_mode_m, triggernum, csrw, csr_tdata1, tdata1_type_six, priv_bits;  // NTRIG
    cp_tinfo_read_only:       cross priv_mode_m, triggernum, csr_tinfo, csr_access;                         // NTRIG
endgroup

covergroup SdtrigSm_mcontrol6_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `include "general/RISCV_coverage_sdtrig_coverpoints.svh"

    triggernum_chain: coverpoint ins.current.csr[CSR_TSELECT] {
        bins chained_pair[] = {[1:`UDB_NUM_TRIGGERS-1]};
    }
    tdata1_type_mcontrol6: coverpoint ins.current.csr[CSR_TDATA1][XLEN-1:XLEN-4] {
        bins mcontrol6 = {4'd6};
    }
    tdata1_m: coverpoint ins.current.csr[CSR_TDATA1][6] {
        bins disabled = {1'b0};
        bins enabled  = {1'b1};
    }
    tdata1_select_adr: coverpoint ins.current.csr[CSR_TDATA1][21] {
        bins adr = {1'b0};
    }
    tdata1_select_data: coverpoint ins.current.csr[CSR_TDATA1][21] {
        bins data = {1'b1};
    }
    tdata1_xsl: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins xsl[] = {[0:7]};
    }
    tdata1_xsl_store: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins store = {3'b010};
    }
    tdata1_xsl_load_store: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins load_store = {3'b011};
    }
    tdata1_xsl_all: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
        bins execute_store_load = {3'b111};
    }
    tdata1_size: coverpoint ins.current.csr[CSR_TDATA1][18:16] {
        bins size[] = {[0:6]};
    }
    tdata1_match_cmp: coverpoint ins.current.csr[CSR_TDATA1][10:7] {
        bins equal     = {4'd0};
        bins ge        = {4'd2};
        bins lt        = {4'd3};
        bins not_equal = {4'd8};
    }
    tdata1_match_napot: coverpoint ins.current.csr[CSR_TDATA1][10:7] {
        bins napot     = {4'd1};
        bins not_napot = {4'd9};
    }
    tdata1_match_mask: coverpoint ins.current.csr[CSR_TDATA1][10:7] {
        bins mask_low      = {4'd4};
        bins mask_high     = {4'd5};
        bins not_mask_low  = {4'd12};
        bins not_mask_high = {4'd13};
    }
    tdata1_chain_disabled: coverpoint ins.current.csr[CSR_TDATA1][11] {
        bins disabled = {1'b0};
    }
    tdata2_pc: coverpoint (ins.current.csr[CSR_TDATA2] == ins.current.pc_rdata) {
        bins pc   = {1'b1};
        bins zero = {1'b0} iff (ins.current.csr[CSR_TDATA2] == '0);
    }
    tdata2_adr: coverpoint (ins.current.csr[CSR_TDATA2] == ins.current.mem_addr) {
        bins scratch = {1'b1};
        bins zero    = {1'b0} iff (ins.current.csr[CSR_TDATA2] == '0);
    }
    tdata2_adr_match: coverpoint (ins.current.csr[CSR_TDATA2] == ins.current.mem_addr) {
        bins match = {1'b1};
    }
    tdata2_nop: coverpoint ins.current.csr[CSR_TDATA2] {
        bins nop  = {NOP};
        bins zero = {'0};
    }
    tdata2_data: coverpoint (ins.current.csr[CSR_TDATA2][31:0] == (ins.current.has_rd ? ins.current.rd_val[31:0] : ins.current.rs2_val[31:0])) {
        bins data = {1'b1};
        bins zero = {1'b0} iff (ins.current.csr[CSR_TDATA2] == '0);
    }
    tdata2_nop_c_nop: coverpoint ins.current.csr[CSR_TDATA2] {
        bins nop   = {NOP};
        bins c_nop = {32'h0001};
    }
    // tdata2 is all ones except one 0 bit; ~tdata2 is then a power of two and $clog2 gives that bit's index
    tdata2_napot: coverpoint $clog2(~ins.current.csr[CSR_TDATA2]) iff ($countones(~ins.current.csr[CSR_TDATA2]) == 1) {
        bins zero_bit[] = {[1:XLEN-1]};
    }
    store_data_cmp: coverpoint ins.current.rs2_val {
        bins zero           = {'0};
        wildcard bins below = {'x} iff (ins.current.rs2_val == ins.current.csr[CSR_TDATA2] - 1);
        wildcard bins equal = {'x} iff (ins.current.rs2_val == ins.current.csr[CSR_TDATA2]);
        wildcard bins above = {'x} iff (ins.current.rs2_val == ins.current.csr[CSR_TDATA2] + 1);
        bins ones           = {'1};
    }
    store_data_napot: coverpoint ins.current.rs2_val {
        bins zero           = {'0};
        wildcard bins other = {'x} iff (ins.current.rs2_val != '0 && ins.current.rs2_val != '1);
        bins ones           = {'1};
    }
    store_data_mask: coverpoint ins.current.rs2_val {
        bins zero               = {'0};
        wildcard bins equal     = {'x} iff (ins.current.rs2_val == ins.current.csr[CSR_TDATA2]);
        wildcard bins low_half  = {'x} iff (ins.current.rs2_val[XLEN/2-1:0]    == ins.current.csr[CSR_TDATA2][XLEN/2-1:0]    && ins.current.rs2_val[XLEN-1:XLEN/2] == '1);
        wildcard bins high_half = {'x} iff (ins.current.rs2_val[XLEN-1:XLEN/2] == ins.current.csr[CSR_TDATA2][XLEN-1:XLEN/2] && ins.current.rs2_val[XLEN/2-1:0]    == '1);
        bins ones               = {'1};
    }
    store_data_chain: coverpoint (ins.current.rs2_val == ins.current.csr[CSR_TDATA2]) {
        bins data = {1'b1};
        bins zero = {1'b0} iff (ins.current.rs2_val == '0);
    }

    store_offset: coverpoint ins.current.imm {
        bins scratch        = {0};
        bins scratch_plus_8 = {8};
    }
    nop: coverpoint ins.current.insn {
        bins nop = {NOP};
    }
    nop_instr: coverpoint ins.current.insn {
        bins nop = {NOP};
        `ifdef ZCA_SUPPORTED
            wildcard bins c_nop = {C_NOP};
        `endif
    }
    sw: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
    }
    lw_sw: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
        wildcard bins lw = {LW};
    }
    store_xlen: coverpoint ins.current.insn {
        `ifdef UDB_MXLEN_64
            wildcard bins sd = {SD};
        `else
            wildcard bins sw = {SW};
        `endif
    }
    load_store_instr: coverpoint ins.current.insn {
        wildcard bins lb  = {LB};
        wildcard bins lbu = {LBU};
        wildcard bins lh  = {LH};
        wildcard bins lhu = {LHU};
        wildcard bins lw  = {LW};
        wildcard bins sb  = {SB};
        wildcard bins sh  = {SH};
        wildcard bins sw  = {SW};
        `ifdef UDB_MXLEN_64
            wildcard bins lwu = {LWU};
            wildcard bins ld  = {LD};
            wildcard bins sd  = {SD};
        `endif
        `ifdef F_SUPPORTED
            wildcard bins flw = {FLW};
            wildcard bins fsw = {FSW};
        `endif
        `ifdef D_SUPPORTED
            wildcard bins fld = {FLD};
            wildcard bins fsd = {FSD};
        `endif
        `ifdef ZFH_SUPPORTED
            wildcard bins flh = {FLH};
            wildcard bins fsh = {FSH};
        `endif
        `ifdef Q_SUPPORTED
            wildcard bins flq = {FLQ};
            wildcard bins fsq = {FSQ};
        `endif
        `ifdef ZCA_SUPPORTED
            wildcard bins c_lw   = {C_LW};
            wildcard bins c_sw   = {C_SW};
            wildcard bins c_lwsp = {C_LWSP};
            wildcard bins c_swsp = {C_SWSP};
            `ifdef UDB_MXLEN_64
                wildcard bins c_ld   = {C_LD};
                wildcard bins c_sd   = {C_SD};
                wildcard bins c_ldsp = {C_LDSP};
                wildcard bins c_sdsp = {C_SDSP};
            `endif
        `endif
        `ifdef ZCB_SUPPORTED
            wildcard bins c_lbu = {C_LBU};
            wildcard bins c_lh  = {C_LH};
            wildcard bins c_lhu = {C_LHU};
            wildcard bins c_sb  = {C_SB};
            wildcard bins c_sh  = {C_SH};
        `endif
        `ifdef ZCF_SUPPORTED
            `ifdef UDB_MXLEN_32
                wildcard bins c_flw   = {C_FLW};
                wildcard bins c_fsw   = {C_FSW};
                wildcard bins c_flwsp = {C_FLWSP};
                wildcard bins c_fswsp = {C_FSWSP};
            `endif
        `endif
        `ifdef ZCD_SUPPORTED
            `ifdef UDB_MXLEN_64
                wildcard bins c_fld   = {C_FLD};
                wildcard bins c_fsd   = {C_FSD};
                wildcard bins c_fldsp = {C_FLDSP};
                wildcard bins c_fsdsp = {C_FSDSP};
            `endif
        `endif
    }

    // main coverpoints
    cp_sdtrig_mcontrol6_priv_mode:       cross priv_mode_m, triggernum, tdata1_type_mcontrol6, tdata1_m, tdata1_select_adr, tdata1_xsl_store, tdata2_adr_match, sw;                                     // NTRIG * 2 m modes
    cp_sdtrig_mcontrol6_execute_adr:     cross priv_mode_m, triggernum, tdata1_type_mcontrol6, tdata1_select_adr, tdata1_xsl, tdata2_pc, nop;                                                           // NTRIG * 8 xsl * 2 tdata2
    cp_sdtrig_mcontrol6_load_store_adr:  cross priv_mode_m, triggernum, tdata1_type_mcontrol6, tdata1_select_adr, tdata1_xsl, tdata2_adr, lw_sw;                                                        // NTRIG * 8 xsl * 2 tdata2 * 2 instrs
    cp_sdtrig_mcontrol6_execute_data:    cross priv_mode_m, triggernum, tdata1_type_mcontrol6, tdata1_select_data, tdata1_xsl, tdata2_nop, nop;                                                         // NTRIG * 8 xsl * 2 tdata2
    cp_sdtrig_mcontrol6_load_store_data: cross priv_mode_m, triggernum, tdata1_type_mcontrol6, tdata1_select_data, tdata1_xsl, tdata2_data, lw_sw;                                                      // NTRIG * 8 xsl * 2 tdata2 * 2 instrs
    cp_sdtrig_mcontrol6_execute_size:    cross priv_mode_m, triggernum, tdata1_type_mcontrol6, tdata1_select_data, tdata1_xsl_all, tdata1_size, tdata2_nop_c_nop, nop_instr;                            // NTRIG * 7 sizes * 2 tdata2 * 2 instrs
    cp_sdtrig_mcontrol6_load_store_size: cross priv_mode_m, triggernum, tdata1_type_mcontrol6, tdata1_select_adr, tdata1_xsl_load_store, tdata1_size, tdata2_adr, load_store_instr;                     // NTRIG * 7 sizes * 2 tdata2 * instrs
    cp_sdtrig_mcontrol6_match:           cross priv_mode_m, triggernum, tdata1_type_mcontrol6, tdata1_select_data, tdata1_xsl_store, tdata1_match_cmp, store_data_cmp, store_xlen;                      // NTRIG * 4 match * 5 values
    cp_sdtrig_mcontrol6_match_napot:     cross priv_mode_m, triggernum, tdata1_type_mcontrol6, tdata1_select_data, tdata1_xsl_store, tdata1_match_napot, tdata2_napot, store_data_napot, store_xlen;    // NTRIG * 2 match * (XLEN-1) tdata2 * 3 values
    cp_sdtrig_mcontrol6_match_mask:      cross priv_mode_m, triggernum, tdata1_type_mcontrol6, tdata1_select_data, tdata1_xsl_store, tdata1_match_mask, store_data_mask, store_xlen;                    // NTRIG * 4 match * 5 values
    cp_sdtrig_mcontrol6_chain_adr:       cross priv_mode_m, triggernum_chain, tdata1_type_mcontrol6, tdata1_select_data, tdata1_chain_disabled, tdata1_xsl_store, store_data_chain, store_offset, sw;   // (NTRIG-1) * 2 data * 2 adr
endgroup

function void sdtrigsm_sample(int hart, int issue, ins_t ins);
    SdtrigSm_trig_module_reg_cg.sample(ins);
    SdtrigSm_mcontrol6_cg.sample(ins);
endfunction
