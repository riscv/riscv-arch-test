///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Julia Gong jgong@g.hmc.edu November 10, 2025
//
// Copyright (C) 2025 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVINVALH
covergroup SvinvalH_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    cp_instr : coverpoint ins.current.insn {
        wildcard bins sfence_inval_ir = {32'b0001100_00001_00000_000_00000_1110011};
        wildcard bins sfence_w_inval  = {32'b0001100_00000_00000_000_00000_1110011};
        wildcard bins sinval_vma      = {32'b0001011_?????_?????_000_00000_1110011};
        wildcard bins hinval_vvma     = {32'b0010011_?????_?????_000_00000_1110011};
        wildcard bins hinval_gvma     = {32'b0110011_?????_?????_000_00000_1110011};
    }
    cp_priv : coverpoint {ins.prev.mode_virt, ins.prev.mode} {
        bins M_mode     = {3'b011};
        bins S_mode     = {3'b001};
        bins U_mode     = {3'b000};
        bins VS_mode    = {3'b101};
        bins VU_mode    = {3'b100};
    }
    cp_tvm : coverpoint ins.prev.csr[12'h300][20] {
    }

    cp_vtvm : coverpoint ins.prev.csr[12'h600][20] { // hstatus.VTVM
    }

    cr_svinivalH : cross cp_instr, cp_priv, cp_tvm, cp_vtvm {
        // each instruction executed in each privilege mode with each TVM
    }
 endgroup

// ---------------------
function void svinvalh_sample(int hart, int issue, ins_t ins);

    SvinvalH_cg.sample(ins);
endfunction
