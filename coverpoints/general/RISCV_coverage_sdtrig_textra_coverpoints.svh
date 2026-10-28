///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   textra (tdata3) building blocks of the SdtrigSm/S/U textra covergroups
//   Weight 0: only the crosses count.
//
///////////////////////////////////////////
mhselect: coverpoint sdtrig_textra_mhselect(ins.current.csr[CSR_TDATA3]) {
    type_option.weight = 0;
    bins ignore   = {3'd0};
    bins mcontext = {3'd4};
}
mhselect_mcontext: coverpoint sdtrig_textra_mhselect(ins.current.csr[CSR_TDATA3]) {
    type_option.weight = 0;
    bins mcontext = {3'd4};
}
sselect: coverpoint sdtrig_textra_sselect(ins.current.csr[CSR_TDATA3]) {
    type_option.weight = 0;
    bins ignore   = {2'd0};
    bins scontext = {2'd1};
}
mhselect_ignore: coverpoint sdtrig_textra_mhselect(ins.current.csr[CSR_TDATA3]) {
    type_option.weight = 0;
    bins ignore = {3'd0};
}
sselect_ignore: coverpoint sdtrig_textra_sselect(ins.current.csr[CSR_TDATA3]) {
    type_option.weight = 0;
    bins ignore = {2'd0};
}
sselect_scontext: coverpoint sdtrig_textra_sselect(ins.current.csr[CSR_TDATA3]) {
    type_option.weight = 0;
    bins scontext = {2'd1};
}
// bytes ignored by sbytemask; with every byte ignored the compare always matches (sbytemask_all)
sbytemask: coverpoint sdtrig_textra_sbytemask(ins.current.csr[CSR_TDATA3]) {
    type_option.weight = 0;
    bins none  = {4'b0000};
    bins byte0 = {4'b0001};
    bins byte1 = {4'b0010};
`ifdef UDB_MXLEN_64
    bins byte2 = {4'b0100};
    bins byte3 = {4'b1000};
`endif
}
sbytemask_all: coverpoint sdtrig_textra_sbytemask(ins.current.csr[CSR_TDATA3]) {
    type_option.weight = 0;
`ifdef UDB_MXLEN_64
    bins all = {4'b1111};
`else
    bins all = {4'b0011};
`endif
}
mcontext_match: coverpoint sdtrig_textra_mcontext_match(ins.current.csr[CSR_TDATA3], ins.current.csr[CSR_MCONTEXT]) {
    type_option.weight = 0;
    bins mismatch = {1'b0};
    bins match    = {1'b1};
}
scontext_match: coverpoint sdtrig_textra_scontext_match(ins.current.csr[CSR_TDATA3], ins.current.csr[CSR_SCONTEXT]) {
    type_option.weight = 0;
    bins mismatch = {1'b0};
    bins match    = {1'b1};
}

sselect_asid: coverpoint sdtrig_textra_sselect(ins.current.csr[CSR_TDATA3]) {
    type_option.weight = 0;
    bins asid = {2'd2};
}
asid_match: coverpoint sdtrig_textra_asid_match(ins.current.csr[CSR_TDATA3], ins.current.csr[CSR_SATP]) {
    type_option.weight = 0;
    bins mismatch = {1'b0};
    bins match    = {1'b1};
}

// cp_textra_mhselect_no_h: a tdata3 write of an mhselect value that needs H, on a trigger armed as icount or mcontrol6
csr_tdata3: coverpoint ins.current.insn[31:20] {
    type_option.weight = 0;
    bins tdata3 = {CSR_TDATA3};
}
armed_type: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "type")[3:0] {
    type_option.weight = 0;
    bins icount    = {4'd3};
    bins mcontrol6 = {4'd6};
}
mhselect_written: coverpoint sdtrig_textra_mhselect(ins.current.rs1_val) {
    type_option.weight = 0;
    bins h_only[] = {3'd1, 3'd2, 3'd3, 3'd5, 3'd6, 3'd7};
}
mhselect_legal: coverpoint sdtrig_textra_mhselect(ins.current.csr[CSR_TDATA3]) {
    type_option.weight = 0;
    bins legal = {3'd0, 3'd4};
}

scontext_match_only: coverpoint sdtrig_textra_scontext_match(ins.current.csr[CSR_TDATA3], ins.current.csr[CSR_SCONTEXT]) {
    type_option.weight = 0;
    bins match = {1'b1};
}
// SdtrigS/U: an instruction that the armed icount or mcontrol6 trigger acts on (sdtrig_textra_action)
textra_action: coverpoint sdtrig_textra_action(ins) {
    type_option.weight = 0;
    bins icount    = {4'd3};
    bins mcontrol6 = {4'd6};
}
