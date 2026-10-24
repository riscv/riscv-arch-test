///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Written: Angela Zheng, angela20061015@gmail.com, 10 September 2026
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   Debug Trigger coverpoints common to SdtrigSm, SdtrigS, SdtrigU
//
///////////////////////////////////////////
// the selected trigger, among those the tests exercise (SDTRIG_TESTED_TRIGGERS, derived_config.svh)
triggernum: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tselect", "tselect") {
    type_option.weight = 0;
    bins all_triggers[] = {[0:`SDTRIG_TESTED_TRIGGERS-1]};
}
// the selected trigger, among the tested triggers that support mcontrol6
`ifdef SDTRIG_MCONTROL6_ANY
triggernum_mcontrol6: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tselect", "tselect") {
    type_option.weight = 0;
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_0 bins trigger_0 = {0}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_1 bins trigger_1 = {1}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_2 bins trigger_2 = {2}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_3 bins trigger_3 = {3}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_4 bins trigger_4 = {4}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_5 bins trigger_5 = {5}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_6 bins trigger_6 = {6}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_7 bins trigger_7 = {7}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_8 bins trigger_8 = {8}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_9 bins trigger_9 = {9}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_10 bins trigger_10 = {10}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_11 bins trigger_11 = {11}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_12 bins trigger_12 = {12}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_13 bins trigger_13 = {13}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_14 bins trigger_14 = {14}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SUPPORTED_TRIGGERS_15 bins trigger_15 = {15}; `endif
}
`endif
// the selected trigger, among the tested triggers that support icount
`ifdef SDTRIG_ICOUNT_ANY
triggernum_icount: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tselect", "tselect") {
    type_option.weight = 0;
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_0 bins trigger_0 = {0}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_1 bins trigger_1 = {1}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_2 bins trigger_2 = {2}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_3 bins trigger_3 = {3}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_4 bins trigger_4 = {4}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_5 bins trigger_5 = {5}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_6 bins trigger_6 = {6}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_7 bins trigger_7 = {7}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_8 bins trigger_8 = {8}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_9 bins trigger_9 = {9}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_10 bins trigger_10 = {10}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_11 bins trigger_11 = {11}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_12 bins trigger_12 = {12}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_13 bins trigger_13 = {13}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_14 bins trigger_14 = {14}; `endif
    `ifdef UDB_SDTRIG_ICOUNT_SUPPORTED_TRIGGERS_15 bins trigger_15 = {15}; `endif
}
`endif
// the selected trigger, among the tested triggers that support itrigger
`ifdef SDTRIG_ITRIGGER_ANY
triggernum_itrigger: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tselect", "tselect") {
    type_option.weight = 0;
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_0 bins trigger_0 = {0}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_1 bins trigger_1 = {1}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_2 bins trigger_2 = {2}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_3 bins trigger_3 = {3}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_4 bins trigger_4 = {4}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_5 bins trigger_5 = {5}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_6 bins trigger_6 = {6}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_7 bins trigger_7 = {7}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_8 bins trigger_8 = {8}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_9 bins trigger_9 = {9}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_10 bins trigger_10 = {10}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_11 bins trigger_11 = {11}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_12 bins trigger_12 = {12}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_13 bins trigger_13 = {13}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_14 bins trigger_14 = {14}; `endif
    `ifdef UDB_SDTRIG_ITRIGGER_SUPPORTED_TRIGGERS_15 bins trigger_15 = {15}; `endif
}
`endif
// the selected trigger, among the tested triggers that support etrigger
`ifdef SDTRIG_ETRIGGER_ANY
triggernum_etrigger: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tselect", "tselect") {
    type_option.weight = 0;
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_0 bins trigger_0 = {0}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_1 bins trigger_1 = {1}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_2 bins trigger_2 = {2}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_3 bins trigger_3 = {3}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_4 bins trigger_4 = {4}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_5 bins trigger_5 = {5}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_6 bins trigger_6 = {6}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_7 bins trigger_7 = {7}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_8 bins trigger_8 = {8}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_9 bins trigger_9 = {9}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_10 bins trigger_10 = {10}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_11 bins trigger_11 = {11}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_12 bins trigger_12 = {12}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_13 bins trigger_13 = {13}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_14 bins trigger_14 = {14}; `endif
    `ifdef UDB_SDTRIG_ETRIGGER_SUPPORTED_TRIGGERS_15 bins trigger_15 = {15}; `endif
}
`endif
// the mode the instruction on this record runs in and a trap on it is taken from or, on an xRET, the mode it returns
// to. A trigger that fires on the first instruction after the T-SBI return (SdtrigS/U) is logged on the xRET record.
exec_mode_m: coverpoint sdtrig_trap_origin(ins) {
    type_option.weight = 0;
    bins M_mode = {2'd3};
}
exec_mode_s: coverpoint sdtrig_trap_origin(ins) {
    type_option.weight = 0;
    bins S_mode = {2'd1};
}
exec_mode_u: coverpoint sdtrig_trap_origin(ins) {
    type_option.weight = 0;
    bins U_mode = {2'd0};
}
csrr: coverpoint ins.current.insn {
    type_option.weight = 0;
    wildcard bins csrr = {CSRR};
}
csrw: coverpoint ins.current.insn {
    type_option.weight = 0;
    wildcard bins csrw = {CSRW};
}
csr_read_write: coverpoint ins.current.insn {
    type_option.weight = 0;
    wildcard bins csrr = {CSRR};
    wildcard bins csrw = {CSRW};
}
csr_tdata1: coverpoint ins.current.insn[31:20] {
    type_option.weight = 0;
    bins tdata1 = {CSR_TDATA1};
}
csr_tdata2: coverpoint ins.current.insn[31:20] {
    type_option.weight = 0;
    bins tdata2 = {CSR_TDATA2};
}
// the type a csrw writes to tdata1
tdata1_write_type: coverpoint ins.current.rs1_val[XLEN-1:XLEN-4] {
    type_option.weight = 0;
    bins icount    = {4'd3};
    bins mcontrol6 = {4'd6};
}
illegal_insn_trap: coverpoint sdtrig_illegal_taken(ins) {
    type_option.weight = 0;
    bins illegal = {1'b1};
}
mret: coverpoint ins.current.insn {
    type_option.weight = 0;
    bins mret = {MRET};
}

// mcontrol6 fields of the selected trigger's tdata1
tdata1_type_mcontrol6: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "type")[3:0] {
    type_option.weight = 0;
    bins mcontrol6 = {4'd6};
}
tdata1_m_on: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "m")[0] {
    type_option.weight = 0;
    bins on = {1'b1};
}
tdata1_s_on: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "s")[0] {
    type_option.weight = 0;
    bins on = {1'b1};
}
tdata1_u_on: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "u")[0] {
    type_option.weight = 0;
    bins on = {1'b1};
}
tdata1_chain_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "chain")[0] {
    type_option.weight = 0;
    bins disabled = {1'b0};
}
tdata1_execute_on: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "execute")[0] {
    type_option.weight = 0;
    bins on = {1'b1};
}
tdata1_action_breakpoint: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "action") {
    type_option.weight = 0;
    bins breakpoint = {0};
}
tdata1_select_adr: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "select")[0] {
    type_option.weight = 0;
    bins adr = {1'b0};
}
tdata1_select_data: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "select")[0] {
    type_option.weight = 0;
    bins data = {1'b1};
}
tdata1_xsl: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "execute")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "store")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "load")[0]} {
    type_option.weight = 0;
    bins xsl[] = {[0:7]};
}
tdata1_xsl_one: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "execute")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "store")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "load")[0]} {
    type_option.weight = 0;
    bins execute = {3'b100};
    bins store   = {3'b010};
    bins load    = {3'b001};
}
tdata1_xsl_store: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "execute")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "store")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "load")[0]} {
    type_option.weight = 0;
    bins store = {3'b010};
}
tdata1_xsl_load_store: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "execute")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "store")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "load")[0]} {
    type_option.weight = 0;
    bins load_store = {3'b011};
}
tdata1_xsl_load_store_execute: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "execute")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "store")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "load")[0]} {
    type_option.weight = 0;
    bins execute = {3'b111};
}
// tdata1 defaults, crossed where a coverpoint does not vary them
tdata1_match_equal: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "match")[3:0] {
    type_option.weight = 0;
    bins equal = {4'd0};
}
tdata1_size_any: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "size")[2:0] {
    type_option.weight = 0;
    bins any = {3'd0};
}
// every size the hart supports (UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES)
tdata1_size: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "size")[2:0] {
    type_option.weight = 0;
    bins any = {3'd0};
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_1 bins size_1 = {3'd1}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_2 bins size_2 = {3'd2}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_3 bins size_3 = {3'd3}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_4 bins size_4 = {3'd4}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_5 bins size_5 = {3'd5}; `endif
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_LEGAL_VALUES_6 bins size_6 = {3'd6}; `endif
}
tdata2_adr: coverpoint (ins.current.csr[CSR_TDATA2] == ins.current.rs1_val + ins.current.imm) {
    type_option.weight = 0;
    bins scratch = {1'b1};
    bins zero    = {1'b0} iff (ins.current.csr[CSR_TDATA2] == '0);
}
// tdata2 relative to the address in rs1 of an instruction without an offset (lr/sc, AMO, cache operation, vector base)
tdata2_rs1: coverpoint ins.current.csr[CSR_TDATA2] {
    type_option.weight = 0;
    wildcard bins rs1  = {'x} iff (ins.current.csr[CSR_TDATA2] == ins.current.rs1_val);
    bins zero          = {'0};
}
tdata2_pc: coverpoint (ins.current.csr[CSR_TDATA2] == ins.current.pc_rdata) {
    type_option.weight = 0;
    bins pc = {1'b1};
}
