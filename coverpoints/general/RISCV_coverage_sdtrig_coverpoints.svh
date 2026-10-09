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
`ifndef UDB_SDTRIG_NUM_TRIGGERS
    `define UDB_SDTRIG_NUM_TRIGGERS 2
`endif

triggernum: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tselect", "tselect") {
    type_option.weight = 0;
    bins all_triggers[] = {[0:`UDB_SDTRIG_NUM_TRIGGERS-1]};
}
csrr: coverpoint ins.current.insn {
    type_option.weight = 0;
    wildcard bins csrr = {CSRR};
}
csrw: coverpoint ins.current.insn {
    type_option.weight = 0;
    wildcard bins csrw = {CSRW};
}
csr_tdata1: coverpoint ins.current.insn[31:20] {
    type_option.weight = 0;
    bins tdata1 = {CSR_TDATA1};
}

// mcontrol6 fields of the selected trigger's tdata1
tdata1_type_mcontrol6: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "type")[3:0] {
    type_option.weight = 0;
    bins mcontrol6 = {4'd6};
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
// tdata1 defaults, crossed where a coverpoint does not vary them
tdata1_match_equal: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "match")[3:0] {
    type_option.weight = 0;
    bins equal = {4'd0};
}
tdata1_size_any: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "size")[2:0] {
    type_option.weight = 0;
    bins any = {3'd0};
}
tdata1_size: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "size")[2:0] {
    type_option.weight = 0;
    bins any = {3'd0};
    `ifdef UDB_SDTRIG_MCONTROL6_SIZE_AVAILABLE
        bins size[] = {[1:6]};
    `endif
}

// tdata2 of the selected trigger against the sampled access
tdata2_adr: coverpoint (ins.current.csr[CSR_TDATA2] == ins.current.rs1_val + ins.current.imm) {
    type_option.weight = 0;
    bins scratch = {1'b1};
    bins zero    = {1'b0} iff (ins.current.csr[CSR_TDATA2] == '0);
}
