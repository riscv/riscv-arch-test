///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   tdata2 address building blocks of the SdtrigSm/SdtrigS address_matches covergroups
//   Weight 0: only the crosses count.
//
///////////////////////////////////////////
tdata2_xlate_value: coverpoint sdtrig_tdata2_xlate_value(ins) {
    type_option.weight = 0;
    bins bare_max_pa = {4'd9};
`ifdef UDB_MXLEN_64
    `ifdef SV39_SUPPORTED
        bins sv39_msb_0 = {4'd1};
        bins sv39_msb_1 = {4'd2};
    `endif
    `ifdef SV48_SUPPORTED
        bins sv48_msb_0 = {4'd3};
        bins sv48_msb_1 = {4'd4};
    `endif
    `ifdef SV57_SUPPORTED
        bins sv57_msb_0 = {4'd5};
        bins sv57_msb_1 = {4'd6};
    `endif
`else
    `ifdef SV32_SUPPORTED
        bins sv32_msb_0 = {4'd7};
        bins sv32_msb_1 = {4'd8};
    `endif
`endif
}
satp_xlate_mode: coverpoint sdtrig_satp_mode(ins) {
    type_option.weight = 0;
`ifdef UDB_MXLEN_64
    `ifdef SV39_SUPPORTED
        bins sv39 = {4'd8};
    `endif
    `ifdef SV48_SUPPORTED
        bins sv48 = {4'd9};
    `endif
    `ifdef SV57_SUPPORTED
        bins sv57 = {4'd10};
    `endif
`else
    `ifdef SV32_SUPPORTED
        bins sv32 = {4'd1};
    `endif
`endif
}
tdata2_xlate_exec: coverpoint sdtrig_tdata2_xlate_exec(ins) {
    type_option.weight = 0;
    bins va_fired     = {2'd1};
    bins pa_not_fired = {2'd2};
}
