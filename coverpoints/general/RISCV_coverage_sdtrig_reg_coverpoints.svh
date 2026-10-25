///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   Trigger-module register building blocks of the SdtrigSm/SdtrigS trig_module_reg covergroups
//   Weight 0: only the crosses count.
//
///////////////////////////////////////////
type_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "type")[3:0] {
    type_option.weight = 0;
    bins disabled = {4'd15};
}
tdata1_type_six: coverpoint ins.current.rs1_val[XLEN-1:XLEN-4] {
    type_option.weight = 0;
    bins mcontrol6 = {4'd6};
}
priv_bits: coverpoint ins.current.rs1_val[26:0] {
    type_option.weight = 0;
    bins priv = {27'b001_1000_0000_0000_0000_0101_1000};
}
// cp_tdata1_dmode: an M-mode write of dmode = 1 with a supported type (tdata1_write_type) leaves dmode = 0
dmode_written: coverpoint ins.current.rs1_val[XLEN-5] {
    type_option.weight = 0;
    bins set = {1'b1};
}
dmode_after: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "dmode")[0] {
    type_option.weight = 0;
    bins clear = {1'b0};
}
csr_tselect: coverpoint ins.current.insn[31:20] {
    type_option.weight = 0;
    bins tselect = {CSR_TSELECT};
}
csr_tdata: coverpoint ins.current.insn[31:20] {
    type_option.weight = 0;
    bins tdata1 = {CSR_TDATA1};
    `ifdef UDB_TDATA2_IMPLEMENTED
        bins tdata2 = {CSR_TDATA2};
    `endif
    `ifdef UDB_TDATA3_IMPLEMENTED
        bins tdata3 = {CSR_TDATA3};
    `endif
}
csr_tinfo: coverpoint ins.current.insn[31:20] {
    type_option.weight = 0;
    bins tinfo = {CSR_TINFO};
}
// cp_tselect_trigs: a csrr of tinfo reports that the selected trigger exists (info != 1) and, when it
// supports mcontrol6 (info bit 6), version >= 1 (Sdtrig_mcontrol6_dependence)
tinfo_exists: coverpoint (ins.current.rd_val[15:0] != 16'h1) {
    type_option.weight = 0;
    bins exists = {1'b1};
}
tinfo_version: coverpoint (!ins.current.rd_val[6] || ins.current.rd_val[31:24] != 8'h0) {
    type_option.weight = 0;
    bins version_ge1 = {1'b1};
}
csr_global_reg: coverpoint ins.current.insn[31:20] {
    type_option.weight = 0;
    bins tselect  = {CSR_TSELECT};
    `ifdef UDB_TCONTROL_IMPLEMENTED
        bins tcontrol = {CSR_TCONTROL};
    `endif
    `ifdef UDB_MCONTEXT_IMPLEMENTED
        bins mcontext = {CSR_MCONTEXT};
    `endif
    `ifdef UDB_SCONTEXT_IMPLEMENTED
        bins scontext = {CSR_SCONTEXT};
    `endif
    `ifdef UDB_HCONTEXT_IMPLEMENTED
        bins hcontext = {CSR_HCONTEXT};
    `endif
}
csr_local_reg: coverpoint ins.current.insn[31:20] {
    type_option.weight = 0;
    bins tdata1 = {CSR_TDATA1};
    `ifdef UDB_TDATA2_IMPLEMENTED
        bins tdata2 = {CSR_TDATA2};
    `endif
    `ifdef UDB_TDATA3_IMPLEMENTED
        bins tdata3 = {CSR_TDATA3};
    `endif
    bins tinfo  = {CSR_TINFO};
}
csr_access: coverpoint ins.current.insn {
    type_option.weight = 0;
    wildcard bins csrrw0 = {CSRRW} iff (ins.current.rs1_val == '0);
    wildcard bins csrrw1 = {CSRRW} iff (ins.current.rs1_val == '1);
}
// cp_tselect_nonexistent: tselect written with the first unimplemented index
tselect_past_last: coverpoint ins.current.rs1_val {
    type_option.weight = 0;
    bins num_triggers = {XLEN'(`UDB_SDTRIG_NUM_TRIGGERS)};
}
