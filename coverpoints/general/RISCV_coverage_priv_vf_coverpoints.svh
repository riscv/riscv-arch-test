///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Written: James (Kaden) Cassidy jacassidy@hmc.edu May 29 2025
//
// Copyright (C) 2025 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   Vector floating-point coverpoints common to Sm_VF_cg, S_VF_cg, H_VF_cg and U_VF_cg
//   Coverpoints that name mstatus/sstatus stay in each covergroup.
//
///////////////////////////////////////////

//cross vtype_prev_vill_clear, vstart_zero, vl_nonzero, no_trap;
std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                    ins.trap == 0
                }
{
    bins true = {1'b1};
}

vector_vector_arithmetic_fp_instruction: coverpoint ins.current.insn[14:0] {
    wildcard bins arithmetic_vv_opcode = {15'b001_?????_1010111};
}

vfmv_f_s : coverpoint ins.current.insn {
    wildcard bins instruction = {VFMV_F_S};
}

fflags_modified_after_clear : coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags") == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags") != 0);

vs1_zero : coverpoint ins.current.vs1_val == 0;
vs2_zero : coverpoint ins.current.vs2_val == 0;
