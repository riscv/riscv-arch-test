///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Shgatpa: hgatp supports Bare and SvNNx4 for each SvNN that satp supports.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SHGATPA
covergroup Shgatpa_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    hgatp: coverpoint ins.current.insn[31:20] {
        bins hgatp = {CSR_HGATP};
    }
    // Bare and SvNNx4 for each SvNN that satp supports, with the other fields zero
    hgatp_mode: coverpoint ins.current.rs1_val {
        bins bare = {0};
        `ifdef UDB_MXLEN_32
            `ifdef SV32_SUPPORTED
                bins sv32x4 = {32'h80000000};
            `endif
        `else
            `ifdef SV39_SUPPORTED
                bins sv39x4 = {64'h8000000000000000};
            `endif
            `ifdef SV48_SUPPORTED
                bins sv48x4 = {64'h9000000000000000};
            `endif
            `ifdef SV57_SUPPORTED
                bins sv57x4 = {64'hA000000000000000};
            `endif
        `endif
    }

    cp_shgatpa: cross priv_mode_hs, csrrw, hgatp, hgatp_mode;
endgroup

function void shgatpa_sample(int hart, int issue, ins_t ins);
    Shgatpa_cg.sample(ins);
endfunction
