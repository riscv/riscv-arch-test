///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Shvsatpa: vsatp supports every MODE that satp supports.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SHVSATPA
covergroup Shvsatpa_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    vsatp: coverpoint ins.current.insn[31:20] {
        bins vsatp = {CSR_VSATP};
    }
    // Each MODE that satp supports, with the other fields zero
    vsatp_mode: coverpoint ins.current.rs1_val {
        bins bare = {0};
        `ifdef UDB_MXLEN_32
            `ifdef SV32_SUPPORTED
                bins sv32 = {32'h80000000};
            `endif
        `else
            `ifdef SV39_SUPPORTED
                bins sv39 = {64'h8000000000000000};
            `endif
            `ifdef SV48_SUPPORTED
                bins sv48 = {64'h9000000000000000};
            `endif
            `ifdef SV57_SUPPORTED
                bins sv57 = {64'hA000000000000000};
            `endif
        `endif
    }

    cp_shvsatpa: cross priv_mode_hs, csrrw, vsatp, vsatp_mode;
endgroup

function void shvsatpa_sample(int hart, int issue, ins_t ins);
    Shvsatpa_cg.sample(ins);
endfunction
