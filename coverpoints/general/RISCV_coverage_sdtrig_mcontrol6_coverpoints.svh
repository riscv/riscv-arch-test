///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   mcontrol6 building blocks of the SdtrigSm/S/U mcontrol6 covergroups
//   Weight 0: only the crosses count.
//
///////////////////////////////////////////
// the second trigger n of a chained pair n-1, n of mcontrol6 triggers
triggernum_chain: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tselect", "tselect") {
    type_option.weight = 0;
    `ifdef SDTRIG_CHAIN_PAIR_1 bins pair_1 = {1}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_2 bins pair_2 = {2}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_3 bins pair_3 = {3}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_4 bins pair_4 = {4}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_5 bins pair_5 = {5}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_6 bins pair_6 = {6}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_7 bins pair_7 = {7}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_8 bins pair_8 = {8}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_9 bins pair_9 = {9}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_10 bins pair_10 = {10}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_11 bins pair_11 = {11}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_12 bins pair_12 = {12}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_13 bins pair_13 = {13}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_14 bins pair_14 = {14}; `endif
    `ifdef SDTRIG_CHAIN_PAIR_15 bins pair_15 = {15}; `endif
}
// the last trigger of a chain of 3 or more starting at trigger 0 (configured last, so selected at the store)
triggernum_chain_end: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tselect", "tselect") {
    type_option.weight = 0;
    `ifdef SDTRIG_CHAIN_3 bins length_3 = {2}; `endif
    `ifdef SDTRIG_CHAIN_4 bins length_4 = {3}; `endif
    `ifdef SDTRIG_CHAIN_5 bins length_5 = {4}; `endif
    `ifdef SDTRIG_CHAIN_6 bins length_6 = {5}; `endif
    `ifdef SDTRIG_CHAIN_7 bins length_7 = {6}; `endif
    `ifdef SDTRIG_CHAIN_8 bins length_8 = {7}; `endif
    `ifdef SDTRIG_CHAIN_9 bins length_9 = {8}; `endif
    `ifdef SDTRIG_CHAIN_10 bins length_10 = {9}; `endif
    `ifdef SDTRIG_CHAIN_11 bins length_11 = {10}; `endif
    `ifdef SDTRIG_CHAIN_12 bins length_12 = {11}; `endif
    `ifdef SDTRIG_CHAIN_13 bins length_13 = {12}; `endif
    `ifdef SDTRIG_CHAIN_14 bins length_14 = {13}; `endif
    `ifdef SDTRIG_CHAIN_15 bins length_15 = {14}; `endif
    `ifdef SDTRIG_CHAIN_16 bins length_16 = {15}; `endif
}
tdata1_m: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "m")[0] {
    type_option.weight = 0;
    bins disabled = {1'b0};
    bins enabled  = {1'b1};
}
tdata1_match_cmp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "match")[3:0] {
    type_option.weight = 0;
    bins equal = {4'd0};
    `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_2 bins ge        = {4'd2}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_3 bins lt        = {4'd3}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_8 bins not_equal = {4'd8}; `endif
}
// add x0, x1, x2 at tdata2 (pc) or with tdata2 = 0 (zero): seen retiring, or as the breakpoint that replaced it
exec_adr_target: coverpoint (sdtrig_exec_fired(ins) && sdtrig_bp_epc(ins) == ins.current.csr[CSR_TDATA2]) ? 2'd1 :
                            (ins.current.insn != 32'h00208033)                    ? 2'd0 :
                            (ins.current.pc_rdata == ins.current.csr[CSR_TDATA2]) ? 2'd1 :
                            (ins.current.csr[CSR_TDATA2] == '0)                   ? 2'd2 : 2'd0 {
    type_option.weight = 0;
    bins pc   = {2'd1};
    bins zero = {2'd2};
}
tdata2_ls_adr: coverpoint (ins.current.csr[CSR_TDATA2] == ins.current.rs1_val     ? 2'd0 :
                           ins.current.csr[CSR_TDATA2] == ins.current.rs1_val + 8 ? 2'd1 :
                           ins.current.csr[CSR_TDATA2] == '0                      ? 2'd2 : 2'd3) {
    type_option.weight = 0;
    bins scratch        = {2'd0};
    bins scratch_plus_8 = {2'd1};
    bins zero           = {2'd2};
}
tdata1_size_ls: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "size")[2:0] {
    type_option.weight = 0;
    bins any = {3'd0};
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_1 bins b8  = {3'd1}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_2 bins b16 = {3'd2}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_3 bins b32 = {3'd3}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_5 bins b64 = {3'd5}; `endif
}
// addi x0, x1, 0 seen retiring, or as the breakpoint that replaced it
exec_data_target: coverpoint ins.current.csr[CSR_TDATA2] iff (sdtrig_exec_fired(ins) || ins.current.insn == 32'h00008013) {
    type_option.weight = 0;
    bins addi_hint = {32'h00008013};
    bins nofire    = {2}; // no instruction in the test has this encoding
}
tdata2_exec_size: coverpoint ins.current.csr[CSR_TDATA2] {
    type_option.weight = 0;
    bins addi_hint = {32'h00008013};
    bins c_nop     = {32'h0001};
}
store_data_cmp: coverpoint (ins.current.rs2_val == '0       ? 3'd0 :
                            ins.current.rs2_val == '1       ? 3'd4 :
                            ins.current.rs2_val == ins.current.csr[CSR_TDATA2] - 1 ? 3'd1 :
                            ins.current.rs2_val == ins.current.csr[CSR_TDATA2]     ? 3'd2 :
                            ins.current.rs2_val == ins.current.csr[CSR_TDATA2] + 1 ? 3'd3 : 3'd5) {
    type_option.weight = 0;
    bins zero  = {3'd0};
    bins below = {3'd1};
    bins equal = {3'd2};
    bins above = {3'd3};
    bins ones  = {3'd4};
}
`ifdef SDTRIG_MATCH_NAPOT
    tdata1_match_napot: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "match")[3:0] {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_1 bins napot     = {4'd1}; `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_9 bins not_napot = {4'd9}; `endif
    }
    tdata2_napot: coverpoint $clog2(~ins.current.csr[CSR_TDATA2] & (ins.current.csr[CSR_TDATA2] + 1)) iff (ins.current.csr[CSR_TDATA2] != '1) {
        type_option.weight = 0;
        bins zero_bit[] = {[0:((`UDB_SDTRIG_MCONTROL6_MASKMAX6 < XLEN-1) ? `UDB_SDTRIG_MCONTROL6_MASKMAX6 : XLEN-1) - 1]};
    }
    store_data_napot: coverpoint ins.current.rs2_val {
        type_option.weight = 0;
        bins zero           = {'0};
        wildcard bins other = {'x} iff (ins.current.rs2_val != '0 && ins.current.rs2_val != '1);
        bins ones           = {'1};
    }
    // cp_mcontrol6_napot_allones: a csrw of all ones to tdata2
    tdata2_write_ones: coverpoint ins.current.rs1_val {
        type_option.weight = 0;
        bins ones = {'1};
    }
`endif
`ifdef SDTRIG_MATCH_MASK
    tdata1_match_mask: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "match")[3:0] {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_4  bins mask_low      = {4'd4};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_5  bins mask_high     = {4'd5};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_12 bins not_mask_low  = {4'd12}; `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_13 bins not_mask_high = {4'd13}; `endif
    }
    // mask low (match 4) ANDs the low half of the data with tdata2[XLEN-1:XLEN/2] and compares it with tdata2[XLEN/2-1:0];
    // mask high (match 5) does the same with the high half of the data. For example tdata2 = 0xF0F0_A0B0 and
    // low-half data 0x0000A0B0 (value), 0x0000A1B2 (differs only outside the mask), 0x0000F0F0 (differs inside the mask),
    // and 0x0001A0B0 (value with a nonzero, ignored high half); the high-half bins mirror these.
    `define SDTRIG_DATA_LO     ins.current.rs2_val[XLEN/2-1:0]
    `define SDTRIG_DATA_HI     ins.current.rs2_val[XLEN-1:XLEN/2]
    `define SDTRIG_MASK_VALUE  ins.current.csr[CSR_TDATA2][XLEN/2-1:0]
    `define SDTRIG_MASK_MASK   ins.current.csr[CSR_TDATA2][XLEN-1:XLEN/2]
    store_data_mask: coverpoint ins.current.rs2_val {
        type_option.weight = 0;
        bins zero                        = {'0};
        wildcard bins equal              = {'x} iff (ins.current.rs2_val == ins.current.csr[CSR_TDATA2]);
        wildcard bins low_value          = {'x} iff (`SDTRIG_DATA_HI == '0 && `SDTRIG_DATA_LO == `SDTRIG_MASK_VALUE);
        wildcard bins low_unmasked_diff  = {'x} iff (`SDTRIG_DATA_HI == '0 && `SDTRIG_DATA_LO != `SDTRIG_MASK_VALUE && (`SDTRIG_DATA_LO & `SDTRIG_MASK_MASK) == `SDTRIG_MASK_VALUE);
        wildcard bins low_masked_diff    = {'x} iff (`SDTRIG_DATA_HI == '0 && (`SDTRIG_DATA_LO & `SDTRIG_MASK_MASK) != `SDTRIG_MASK_VALUE);
        wildcard bins low_value_high_nz  = {'x} iff (`SDTRIG_DATA_LO == `SDTRIG_MASK_VALUE && `SDTRIG_DATA_HI != '0);
        wildcard bins high_value         = {'x} iff (`SDTRIG_DATA_LO == '0 && `SDTRIG_DATA_HI == `SDTRIG_MASK_VALUE);
        wildcard bins high_unmasked_diff = {'x} iff (`SDTRIG_DATA_LO == '0 && `SDTRIG_DATA_HI != `SDTRIG_MASK_VALUE && (`SDTRIG_DATA_HI & `SDTRIG_MASK_MASK) == `SDTRIG_MASK_VALUE);
        wildcard bins high_masked_diff   = {'x} iff (`SDTRIG_DATA_LO == '0 && (`SDTRIG_DATA_HI & `SDTRIG_MASK_MASK) != `SDTRIG_MASK_VALUE);
        wildcard bins high_value_low_nz  = {'x} iff (`SDTRIG_DATA_HI == `SDTRIG_MASK_VALUE && `SDTRIG_DATA_LO != '0);
        bins ones                        = {'1};
    }
    `undef SDTRIG_DATA_LO
    `undef SDTRIG_DATA_HI
    `undef SDTRIG_MASK_VALUE
    `undef SDTRIG_MASK_MASK
`endif
store_data_chain: coverpoint (ins.current.rs2_val == ins.current.csr[CSR_TDATA2]) {
    type_option.weight = 0;
    bins data = {1'b1};
    bins zero = {1'b0} iff (ins.current.rs2_val == '0);
}
store_offset: coverpoint ins.current.imm {
    type_option.weight = 0;
    bins scratch        = {0};
    bins scratch_plus_8 = {8};
}
exec_size_target: coverpoint sdtrig_exec_size_target(ins) {
    type_option.weight = 0;
    bins addi_hint = {2'd1};
    `ifdef ZCA_SUPPORTED
        bins c_nop = {2'd2};
    `endif
}
`ifdef SDTRIG_EXEC_ADR_SIZE
    // the size and target pairs on which Sail 0.16 and the Debug spec agree (sail-riscv#2033): one bin each
    exec_adr_size_case: coverpoint sdtrig_exec_adr_size_case(ins) {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_1
            bins size_1_addi = {4'd2};
            `ifdef ZCA_SUPPORTED bins size_1_c_nop = {4'd3}; `endif
        `endif
        `ifdef ZCA_SUPPORTED
            `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_2 bins size_2_c_nop = {4'd5}; `endif
        `endif
        `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_3 bins size_3_addi = {4'd6}; `endif
        `ifdef UDB_MXLEN_64
            `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_4
                bins size_4_addi = {4'd8};
                `ifdef ZCA_SUPPORTED bins size_4_c_nop = {4'd9}; `endif
            `endif
            `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_5
                bins size_5_addi = {4'd10};
                `ifdef ZCA_SUPPORTED bins size_5_c_nop = {4'd11}; `endif
            `endif
        `endif
    }
`endif
sw: coverpoint ins.current.insn {
    type_option.weight = 0;
    wildcard bins sw = {SW};
}
lw_sw: coverpoint ins.current.insn {
    type_option.weight = 0;
    wildcard bins sw = {SW};
    wildcard bins lw = {LW};
}
// XLEN-wide load and store, for select = data matches with size = 0 (any)
load_store_xlen: coverpoint ins.current.insn {
    type_option.weight = 0;
    `ifdef UDB_MXLEN_64
        wildcard bins sd = {SD};
        wildcard bins ld = {LD};
    `else
        wildcard bins sw = {SW};
        wildcard bins lw = {LW};
    `endif
}
store_xlen: coverpoint ins.current.insn {
    type_option.weight = 0;
    `ifdef UDB_MXLEN_64
        wildcard bins sd = {SD};
    `else
        wildcard bins sw = {SW};
    `endif
}
load_store_instr: coverpoint ins.current.insn {
    type_option.weight = 0;
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
        wildcard bins c_fld   = {C_FLD};
        wildcard bins c_fsd   = {C_FSD};
        wildcard bins c_fldsp = {C_FLDSP};
        wildcard bins c_fsdsp = {C_FSDSP};
    `endif
}
// cp_mcontrol6_size_data: a select = data store trigger with size = N on an sb/sh/sw/sd
tdata1_size_data: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "size")[2:0] {
    type_option.weight = 0;
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_1 bins b8  = {3'd1}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_2 bins b16 = {3'd2}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_3 bins b32 = {3'd3}; `endif
    `ifdef UDB_MXLEN_64
        `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_5 bins b64 = {3'd5}; `endif
    `endif
}
size_data_case: coverpoint sdtrig_size_data_case(ins) {
    type_option.weight = 0;
    bins width_match_low_equal  = {2'd1};
    bins width_match_low_differ = {2'd2};
    bins width_differs          = {2'd3};
}
size_data_outcome: coverpoint sdtrig_bp_taken(ins) == (sdtrig_size_data_case(ins) == 2'd1) {
    type_option.weight = 0;
    bins as_expected = {1'b1};
}
// cp_mcontrol6_match_size_*: the match, size and case of a select = 1 trigger (sdtrig_ms_case)
`ifdef SDTRIG_SIZE_DATA
    ms_match: coverpoint get_csr_val(ins.hart, ins.issue, sdtrig_ms_when(ins), "tdata1", "match")[3:0] {
        type_option.weight = 0;
        bins equal = {4'd0};
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_1  bins napot         = {4'd1};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_2  bins ge            = {4'd2};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_3  bins lt            = {4'd3};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_4  bins mask_low      = {4'd4};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_5  bins mask_high     = {4'd5};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_8  bins not_equal     = {4'd8};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_9  bins not_napot     = {4'd9};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_12 bins not_mask_low  = {4'd12}; `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_13 bins not_mask_high = {4'd13}; `endif
    }
    ms_size_data: coverpoint get_csr_val(ins.hart, ins.issue, sdtrig_ms_when(ins), "tdata1", "size")[2:0] {
        type_option.weight = 0;
        `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_1 bins b8  = {3'd1}; `endif
        `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_2 bins b16 = {3'd2}; `endif
        `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_3 bins b32 = {3'd3}; `endif
        `ifdef UDB_MXLEN_64
            `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_5 bins b64 = {3'd5}; `endif
        `endif
    }
    ms_store_case: coverpoint sdtrig_ms_case(ins, 3'b010) {
        type_option.weight = 0;
        bins size_fired     = {2'd1};
        bins size_not_fired = {2'd2};
        bins other_width    = {2'd3};
    }
    ms_load_case: coverpoint sdtrig_ms_case(ins, 3'b001) {
        type_option.weight = 0;
        bins size_fired     = {2'd1};
        bins size_not_fired = {2'd2};
        bins other_width    = {2'd3};
    }
`endif
`ifdef SDTRIG_MATCH_SIZE_EXEC
    // On RV64 the high half of an instruction is 0, so mask high (5) and not mask high (13) on a 32-bit
    // instruction either fire on every instruction, including the csrw that disarms the trigger, or on none:
    // only the never-firing groups are tested, and the crosses leave those matches out
    ms_match_exec: coverpoint get_csr_val(ins.hart, ins.issue, sdtrig_ms_when(ins), "tdata1", "match")[3:0] {
        type_option.weight = 0;
        bins equal = {4'd0};
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_1  bins napot         = {4'd1};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_2  bins ge            = {4'd2};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_3  bins lt            = {4'd3};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_4  bins mask_low      = {4'd4};  `endif
        `ifndef UDB_MXLEN_64
            `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_5  bins mask_high     = {4'd5};  `endif
        `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_8  bins not_equal     = {4'd8};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_9  bins not_napot     = {4'd9};  `endif
        `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_12 bins not_mask_low  = {4'd12}; `endif
        `ifndef UDB_MXLEN_64
            `ifdef UDB_SDTRIG_MCONTROL6_MATCH_LEGAL_VALUES_13 bins not_mask_high = {4'd13}; `endif
        `endif
    }
    ms_size_exec: coverpoint get_csr_val(ins.hart, ins.issue, sdtrig_ms_when(ins), "tdata1", "size")[2:0] {
        type_option.weight = 0;
        `ifdef SDTRIG_MATCH_SIZE_EXEC16 bins b16 = {3'd2}; `endif
        `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_3 bins b32 = {3'd3}; `endif
    }
    ms_exec_case: coverpoint sdtrig_ms_case(ins, 3'b100) {
        type_option.weight = 0;
        bins size_fired     = {2'd1};
        bins size_not_fired = {2'd2};
    }
    `ifdef SDTRIG_MATCH_SIZE_EXEC16
        // a 32-bit instruction against a size = 2 trigger: a 32-bit trigger's own disarming csrw rules out
        // some tdata2 values for 16-bit instructions on size = 3, so only this direction is required
        ms_size_exec16: coverpoint get_csr_val(ins.hart, ins.issue, sdtrig_ms_when(ins), "tdata1", "size")[2:0] {
            type_option.weight = 0;
            bins b16 = {3'd2};
        }
        ms_exec_other: coverpoint sdtrig_ms_case(ins, 3'b100) {
            type_option.weight = 0;
            bins other_width = {2'd3};
        }
    `endif
`endif
// cp_mcontrol6_chain_long: the XLEN-wide store of x0 to the address the chain's last trigger watches, and
// whether the breakpoint was taken on it
chain_store_x0: coverpoint ins.current.insn[24:20] {
    type_option.weight = 0;
    bins x0 = {5'd0};
}
chain_store_adr: coverpoint (ins.current.csr[CSR_TDATA2] == ins.current.rs1_val + ins.current.imm) {
    type_option.weight = 0;
    bins watched = {1'b1};
}
chain_fired: coverpoint sdtrig_bp_taken(ins) {
    type_option.weight = 0;
    bins fired     = {1'b1};
    bins not_fired = {1'b0};
}
`ifndef SDTRIG_SUITE_SM
// SdtrigS/U cp_mcontrol6_priv_bits: a sw to the address watched by an mcontrol6 store trigger (select = 0, store = 1)
// and whether it fired as the trigger's m/s/u bits require (sdtrig_priv_bits_outcome)
priv_bits_sw: coverpoint ins.current.insn iff (
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "type")[3:0] == 4'd6 &&
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "store")[0] &&
        !get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "select")[0] &&
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata2", "tdata2") == ins.current.rs1_val + ins.current.imm) {
    type_option.weight = 0;
    wildcard bins sw = {SW};
}
priv_bits_outcome: coverpoint sdtrig_priv_bits_outcome(ins, `SDTRIG_MCONTROL6_MODE_BIT) {
    type_option.weight = 0;
    bins own_fired      = {2'd1};
    bins others_no_fire = {2'd2};
}
`endif
