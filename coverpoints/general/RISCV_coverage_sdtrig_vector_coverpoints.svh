///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   Vector load/store building blocks of the SdtrigSm/S/U combined_accesses covergroups
//   Weight 0: only the crosses count.
//
///////////////////////////////////////////
vec_access: coverpoint ins.current.insn {
    type_option.weight = 0;
    wildcard bins vle8  = {VLE8_V};
    wildcard bins vle16 = {VLE16_V};
    wildcard bins vle32 = {VLE32_V};
    wildcard bins vse8  = {VSE8_V};
    wildcard bins vse16 = {VSE16_V};
    wildcard bins vse32 = {VSE32_V};
    `ifdef ZVE64X_SUPPORTED
        wildcard bins vle64 = {VLE64_V};
        wildcard bins vse64 = {VSE64_V};
    `endif
}
// the trigger watches the direction of the access: load (x/s/l = 001) for vle, store (010) for vse
vec_xsl: coverpoint {ins.current.insn[6:0] == 7'b0100111, get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "execute")[0],
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "store")[0], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "load")[0]} {
    type_option.weight = 0;
    bins access_direction = {4'b0_001, 4'b1_010};
}
vec_unmasked: coverpoint ins.current.insn[25] {
    type_option.weight = 0;
    bins unmasked = {1'b1};
}
vec_masked: coverpoint ins.current.insn[25] {
    type_option.weight = 0;
    bins masked = {1'b0};
}
// vl = 1 accesses only the element at the base; vsetivli with AVL 9 gives a vl that reaches base + 8 (vl = VLMAX < 9
// for SEW 64 at VLEN 128)
vec_vl: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vl", "vl") == 1 ? 2'd1 :
                    get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vl", "vl") * sdtrig_vec_eew_bytes(ins.current.insn) > 8 ? 2'd2 : 2'd0) {
    type_option.weight = 0;
    bins one       = {2'd1};
    bins reaches_8 = {2'd2};
}
vec_vl_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vl", "vl") {
    type_option.weight = 0;
    bins one = {1};
}
vec_vl_reaches_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vl", "vl") * sdtrig_vec_eew_bytes(ins.current.insn) > 8 {
    type_option.weight = 0;
    bins reaches_8 = {1'b1};
}
// tdata2 relative to the base address in rs1
vec_tdata2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata2", "tdata2") {
    type_option.weight = 0;
    wildcard bins base        = {'x} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata2", "tdata2") == ins.current.rs1_val);
    wildcard bins base_plus_8 = {'x} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata2", "tdata2") == ins.current.rs1_val + 8);
    bins zero                 = {'0};
}
vec_tdata2_plus_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata2", "tdata2") {
    type_option.weight = 0;
    wildcard bins base_plus_8 = {'x} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata2", "tdata2") == ins.current.rs1_val + 8);
}
// v0 mask bit of the element at base + 8
vec_element_8: coverpoint ins.current.v_wdata[0][8 / sdtrig_vec_eew_bytes(ins.current.insn)] {
    type_option.weight = 0;
    bins masked_off = {1'b0};
    bins active     = {1'b1};
}
// fired (into M, mcause = 3) iff an active element below vl matches
vec_outcome: coverpoint sdtrig_vec_as_expected(ins) {
    type_option.weight = 0;
    bins as_expected = {1'b1};
}
