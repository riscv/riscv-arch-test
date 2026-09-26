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
`ifndef UDB_NUM_TRIGGERS
    `define UDB_NUM_TRIGGERS 2
`endif

triggernum: coverpoint ins.current.csr[CSR_TSELECT] {
    type_option.weight = 0;
    bins all_triggers[] = {[0:`UDB_NUM_TRIGGERS-1]};
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
nop: coverpoint ins.current.insn {
    type_option.weight = 0;
    bins nop = {NOP};
}

// mcontrol6 fields of the selected trigger's tdata1
tdata1_type_mcontrol6: coverpoint ins.current.csr[CSR_TDATA1][XLEN-1:XLEN-4] {
    type_option.weight = 0;
    bins mcontrol6 = {4'd6};
}
tdata1_select_adr: coverpoint ins.current.csr[CSR_TDATA1][21] {
    type_option.weight = 0;
    bins adr = {1'b0};
}
tdata1_select_data: coverpoint ins.current.csr[CSR_TDATA1][21] {
    type_option.weight = 0;
    bins data = {1'b1};
}
tdata1_xsl: coverpoint ins.current.csr[CSR_TDATA1][2:0] {
    type_option.weight = 0;
    bins xsl[] = {[0:7]};
}
tdata1_size: coverpoint ins.current.csr[CSR_TDATA1][18:16] {
    type_option.weight = 0;
    bins size[] = {[0:6]};
}

// tdata2 of the selected trigger against the sampled access
tdata2_adr: coverpoint (ins.current.csr[CSR_TDATA2] == ins.current.mem_addr) {
    type_option.weight = 0;
    bins scratch = {1'b1};
    bins zero    = {1'b0} iff (ins.current.csr[CSR_TDATA2] == '0);
}
tdata2_data: coverpoint (ins.current.csr[CSR_TDATA2][31:0] == (ins.current.has_rd ? ins.current.rd_val[31:0] : ins.current.rs2_val[31:0])) {
    type_option.weight = 0;
    bins data = {1'b1};
    bins zero = {1'b0} iff (ins.current.csr[CSR_TDATA2] == '0);
}
