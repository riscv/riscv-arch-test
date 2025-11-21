///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVINVAL
covergroup Svinval_cg with function sample(ins_t ins);
    option.per_instance = 0;
    cp_instr : coverpoint ins.current.insn {
        wildcard bins sfence_inval_ir = {32'b0001100_00001_00000_000_00000_1110011};
        wildcard bins sfence_w_inval  = {32'b0001100_00000_00000_000_00000_1110011};
        wildcard bins sinval_vma      = {32'b0001011_?????_?????_000_00000_1110011};
        wildcard bins sfence_vma      = {32'b0001001_?????_?????_000_00000_1110011}; // not essential, but might as well cross it
    }
    cp_priv : coverpoint {ins.prev.mode} {
        bins M_mode     = {2'b11};
        bins S_mode     = {2'b01};
        bins U_mode     = {2'b00};
    }
    cp_tvm : coverpoint ins.prev.csr[12'h300][20] {
    }
    cr_svinival : cross cp_instr, cp_priv, cp_tvm {
        // each instruction executed in each privilege mode with each TVM
    }
 endgroup

// ---------------------
function void svinval_sample(int hart, int issue, ins_t ins);

    //$display("Svinval coverage: ins_str %s ins,prev.mode %b tvm %b", ins.ins_str, ins.prev.mode, ins.prev.csr[12'h300][20]);
    Svinval_cg.sample(ins);
endfunction
