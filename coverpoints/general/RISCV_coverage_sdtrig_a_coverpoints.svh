///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   lr/sc and AMO building blocks of the SdtrigSm/S/U a covergroups
//   Weight 0: only the crosses count.
//
///////////////////////////////////////////
a_tdata2_data: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata2", "tdata2") {
    type_option.weight = 0;
    wildcard bins value = {'x} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata2", "tdata2") != '0);
    bins zero           = {'0};
}
lrsc_op: coverpoint ins.current.insn {
    type_option.weight = 0;
    wildcard bins lr_w = {LR_W};
    wildcard bins sc_w = {SC_W};
    `ifdef UDB_MXLEN_64
        wildcard bins lr_d = {LR_D};
        wildcard bins sc_d = {SC_D};
    `endif
}
// data matches with size = 0 are defined only for XLEN-wide accesses
lrsc_op_xlen: coverpoint ins.current.insn {
    type_option.weight = 0;
    `ifdef UDB_MXLEN_64
        wildcard bins lr_d = {LR_D};
        wildcard bins sc_d = {SC_D};
    `else
        wildcard bins lr_w = {LR_W};
        wildcard bins sc_w = {SC_W};
    `endif
}
amo_op: coverpoint ins.current.insn {
    type_option.weight = 0;
    wildcard bins amoswap_w = {AMOSWAP_W};
    wildcard bins amoadd_w  = {AMOADD_W};
    wildcard bins amoand_w  = {AMOAND_W};
    wildcard bins amoor_w   = {AMOOR_W};
    wildcard bins amoxor_w  = {AMOXOR_W};
    wildcard bins amomax_w  = {AMOMAX_W};
    wildcard bins amomaxu_w = {AMOMAXU_W};
    wildcard bins amomin_w  = {AMOMIN_W};
    wildcard bins amominu_w = {AMOMINU_W};
    `ifdef UDB_MXLEN_64
        wildcard bins amoswap_d = {AMOSWAP_D};
        wildcard bins amoadd_d  = {AMOADD_D};
        wildcard bins amoand_d  = {AMOAND_D};
        wildcard bins amoor_d   = {AMOOR_D};
        wildcard bins amoxor_d  = {AMOXOR_D};
        wildcard bins amomax_d  = {AMOMAX_D};
        wildcard bins amomaxu_d = {AMOMAXU_D};
        wildcard bins amomin_d  = {AMOMIN_D};
        wildcard bins amominu_d = {AMOMINU_D};
    `endif
}
// fired (into M, mcause = 3) iff the trigger matches the access as a load or store
a_outcome: coverpoint sdtrig_a_as_expected(ins) {
    type_option.weight = 0;
    bins as_expected = {1'b1};
}
