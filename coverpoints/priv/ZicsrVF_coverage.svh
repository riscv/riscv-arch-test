///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: James (Kaden) Cassidy jacassidy@hmc.edu May 29 2025
//
// Copyright (C) 2025 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZICSRVF

covergroup ZicsrVF_cg with function sample(ins_t ins);
    option.per_instance = 0;

    //cross vtype_prev_vill_clear, vstart_zero, vl_nonzero, no_trap;
    std_vec: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        ins.trap == 0
                    }
    {
        bins true = {1'b1};
    }

    //cross vtype_prev_vill_clear, vstart_zero, vl_nonzero;
    std_trap_vec : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") != 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "vs") != 0
                    }
    {
        bins true = {1'b1};
    }

    /////////////////////////////////////////////////////////////////////////////////////////////////////////

    mstatus_fs_initial_clean : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        bins initial = {1};
        bins clean  = {2};
    }

    mstatus_fs_off : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "fs") {
        bins off = {0};
    }

    vector_vector_arithmetic_fp_instruction: coverpoint ins.current.insn[14:0] {
        wildcard bins arithmetic_vv_opcode = {15'b001_?????_1010111};
    }

    vfmv_f_s : coverpoint ins.current.insn {
        wildcard bins instruction = {32'b010000_?_?????_00000_001_?????_1010111};
    }

    fflags_modified_after_clear : coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "fcsr", "fflags") == 0 & get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", "fflags") != 0);

    vs1_zero : coverpoint ins.current.vs1_val == 0;
    vs2_zero : coverpoint ins.current.vs2_val == 0;

    cp_vectorfp_mstatus_fs_state_affecting_register : cross std_vec, vfmv_f_s, mstatus_fs_initial_clean;
    cp_vectorfp_mstatus_fs_state_affecting_csr      : cross std_vec, vector_vector_arithmetic_fp_instruction, mstatus_fs_initial_clean, fflags_modified_after_clear;
    cp_vectorfp_mstatus_fs_state_nonaffecting       : cross std_vec, vector_vector_arithmetic_fp_instruction, mstatus_fs_initial_clean, vs1_zero, vs2_zero;
    cp_vectorfp_mstatus_fs_off                      : cross std_trap_vec, vector_vector_arithmetic_fp_instruction, mstatus_fs_off, vs1_zero, vs2_zero;

endgroup

function void zicsrvf_sample(int hart, int issue, ins_t ins);
    ZicsrVF_cg.sample(ins);
endfunction
