///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: James (Kaden) Cassidy jacassidy@hmc.edu May 29 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SSSTRICTV

covergroup SsstrictV_vcsr_cg with function sample(ins_t ins);
    option.per_instance = 0;

    test: coverpoint ins.current.insn[0] {
        bins one    = {0};
        bins two    = {1};
        bins one_one    = {1'b0};
        bins one_two    = {1'b1};
    }

    // Test: coverpoint ins.current.insn[31:29] {
    //     bins one    = {3'b000};
    //     bins two    = {3'b001};
    //     bins three  = {3'b010};
    //     bins four   = {3'b011};
    //     bins five   = {3'b100};
    //     bins six    = {3'b101};
    //     bins seven  = {3'b110};
    //     bins eight  = {3'b111};
    // }

endgroup

covergroup SsstrictV_instr_cg with function sample(ins_t ins);
    option.per_instance = 0;

    test: coverpoint ins.current.insn[0] {
        bins one    = {0};
        bins two    = {1};
    }

    test_two: coverpoint ins.current.insn[3:0] {
        wildcard bins range = {[3'b?00: 3'b?01], [3'b?10: 3'b?11]};
    }

    // Test: coverpoint ins.current.insn[31:29] {
    //     bins one    = {3'b000};
    //     bins two    = {3'b001};
    //     bins three  = {3'b010};
    //     bins four   = {3'b011};
    //     bins five   = {3'b100};
    //     bins six    = {3'b101};
    //     bins seven  = {3'b110};
    //     bins eight  = {3'b111};
    // }

endgroup

// covergroup ExceptionsV_reserved_cg with function sample(ins_t ins);

//     vtype_prev_vill_clear: coverpoint 1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill")) {
//         bins vill_clear = {1'b0};
//     }

//     vtype_prev_vill_set: coverpoint 1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill")) {
//         bins vill_set = {1'b1};
//     }

//     reserved_vcsrs: coverpoint ins.current.insn[31:20] {
//         bins first      = {12'h00B};
//         bins second     = {12'h00C};
//         bins third      = {12'h00D};
//         bins fourth     = {12'h00E};
//     }

//     csrops: coverpoint ins.current.insn {
//         wildcard bins csrrs     = {32'b????????????_?????_010_?????_1110011};
//         wildcard bins csrrc     = {32'b????????????_?????_011_?????_1110011};
//         wildcard bins csrrw     = {32'b????????????_?????_001_?????_1110011};
//     }

//     csrops_reserved_vcsrs: cross csrops, reserved_vcsrs;

//     vset_i_vl_i_instructions: coverpoint ins.current.insn {
//         wildcard bins vsetvl   =   {32'b1000000_?????_?????_111_?????_1010111};
//         wildcard bins vsetvli  =   {32'b0000_?_?_???_???_?????_111_?????_1010111};
//         wildcard bins vsetivli =   {32'b1100_?_?_???_???_?????_111_?????_1010111};
//     }

//     vsew_reserved: coverpoint ins.current.insn[25:23] {
//         wildcard bins reserved = {3'b1??};
//     }

//     vset_i_vl_i_reserved_vsew: cross vsew_reserved, vset_i_vl_i_instructions;

//     //attempt to set lmul to all values
//     vtype_lmul: coverpoint ins.prev.insn[22:20] {
//         //autofill 000-111
//     }

//     lmul_vset_i_vl_i: cross vset_i_vl_i_instructions, vtype_lmul;

//     vector_vector_arithmetic_instruction: coverpoint ins.current.insn[14:0] {
//         bins arithmetic_vv_opcode = {15'b000_?????_1010111};
//     }

//     lmul2_vd_off_group:   cross vector_vector_arithmetic_instruction, vd_reg_notdiv_2, vs1_reg_div_2, vs2_reg_div_2, vtype_prev_vill_clear;
//     lmul2_vs1_off_group:  cross vector_vector_arithmetic_instruction, vd_reg_div_2, vs1_reg_notdiv_2, vs2_reg_div_2, vtype_prev_vill_clear;
//     lmul2_vs2_off_group:  cross vector_vector_arithmetic_instruction, vd_reg_div_2, vs1_reg_div_2, vs2_reg_notdiv_2, vtype_prev_vill_clear;

//     lmul4_vd_off_group:   cross vector_vector_arithmetic_instruction, vd_reg_notdiv_4, vs1_reg_div_4, vs2_reg_div_4, vtype_prev_vill_clear;
//     lmul4_vs1_off_group:  cross vector_vector_arithmetic_instruction, vd_reg_div_4, vs1_reg_notdiv_4, vs2_reg_div_4, vtype_prev_vill_clear;
//     lmul4_vs2_off_group:  cross vector_vector_arithmetic_instruction, vd_reg_div_4, vs1_reg_div_4, vs2_reg_notdiv_4, vtype_prev_vill_clear;

//     lmul8_vd_off_group:   cross vector_vector_arithmetic_instruction, vd_reg_notdiv_8, vs1_reg_div_8, vs2_reg_div_8, vtype_prev_vill_clear;
//     lmul8_vs1_off_group:  cross vector_vector_arithmetic_instruction, vd_reg_div_8, vs1_reg_notdiv_8, vs2_reg_div_8, vtype_prev_vill_clear;
//     lmul8_vs2_off_group:  cross vector_vector_arithmetic_instruction, vd_reg_div_8, vs1_reg_div_8, vs2_reg_notdiv_8, vtype_prev_vill_clear;

//     vector_load: coverpoint ins.current.insn {
//         wildcard bins vle_v    =  {32'b???_?_00_?_00000_?????_???_?????_0000111};
//         wildcard bins vleff_v  = {32'b???_?_00_?_10000_?????_???_?????_0000111};
//         wildcard bins vlse_v   = {32'b???_?_10_?_?????_?????_???_?????_0000111};
//         wildcard bins vluxei_v = {32'b???_?_01_?_?????_?????_???_?????_0000111};
//         wildcard bins vloxei_v = {32'b???_?_11_?_?????_?????_???_?????_0000111};
//         wildcard bins vlre_v   = {32'b???_?_00_?_01000_?????_???_?????_0000111};
//         wildcard bins vlm_v    = {32'b???_?_00_?_01011_?????_???_?????_0000111};
//     }

//     mew_set: coverpoint ins.current.insn[28] {
//         bins active = {1'b1};
//     }

//     vector_load_mew_set: cross vector_load, mew_set, vtype_prev_vill_clear;

//     vsetvl_i_instructions: coverpoint ins.current.insn {
//         wildcard bins vsetvl   =   {32'b1000000_?????_?????_111_?????_1010111};
//         wildcard bins vsetvli  =   {32'b0000_?_?_???_???_?????_111_?????_1010111};
//     }

//     vd_v0: coverpoint ins.current.insn[11:7] {
//         bins zero = {5'b0};
//     }

//     vs1_v0: coverpoint ins.current.insn[19:15] {
//         bins zero = {5'b0};
//     }

//     vill_clear_post_instruction: coverpoint 1'(get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vtype", "vill")) {
//         bins clear = {1'b0};
//     }

//     //TODO need to devise way to make vlmax change (likely requiring function and boolean coverpoint)
//     vsetvl_i_x0_x0_vlmax_change: cross vsetvl_i_instructions, vd_v0, vs1_v0, vtype_prev_vill_clear, vill_clear_post_instruction;
//     vsetvl_i_x0_x0_vill_set: cross vsetvl_i_instructions, vd_v0, vs1_v0, vtype_prev_vill_set, vill_clear_post_instruction;

//     //TODO EMUL < 1/8 (possible?)

//     //EMUL > 8
//     //for load instructions only (since EEW is in instruction)
//     EMUL_2x_LMUL: coverpoint {ins.current.insn[14:12], 3'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew"))} {
//         //width[2:0] sew[2:0]
//         `ifdef SEW8_SUPPORTED
//         `ifdef SEW16_SUPPORTED
//         bins eew16_sew8: {6'b001_000};
//         `endif
//         `endif

//         `ifdef SEW16_SUPPORTED
//         `ifdef SEW32_SUPPORTED
//         bins eew32_sew16: {6'b010_001};
//         `endif
//         `endif

//         `ifdef SEW32_SUPPORTED
//         `ifdef SEW64_SUPPORTED
//         bins eew64_sew32: {6'b011_010};
//         `endif
//         `endif
//     }

//     NFIELDS_UPTO_4: coverpoint ins.current.insn[31:29] {
//         bins one    = {3'b000};
//         bins two    = {3'b001};
//         bins three  = {3'b010};
//         bins four   = {3'b011};
//     }

//     NFIELDS_UPTO_2: coverpoint ins.current.insn[31:29] {
//         bins one    = {3'b000};
//         bins two    = {3'b001};
//     }

//     NFIELDS_1: coverpoint ins.current.insn[31:29] {
//         bins pass    = {3'b000};
//     }

//     vector_load_emul_16: cross vector_load, EMUL_2x_LMUL, vtype_lmul_8, vtype_prev_vill_clear;

//     vector_load_emul_2_vd_off_group: cross vector_load, EMUL_2x_LMUL, vtype_lmul_1, vd_reg_notdiv_2, vtype_prev_vill_clear, NFIELDS_UPTO_4;
//     vector_load_emul_4_vd_off_group: cross vector_load, EMUL_2x_LMUL, vtype_lmul_2, vd_reg_notdiv_4, vtype_prev_vill_clear, NFIELDS_UPTO_2;
//     vector_load_emul_8_vd_off_group: cross vector_load, EMUL_2x_LMUL, vtype_lmul_4, vd_reg_notdiv_8, vtype_prev_vill_clear, NFIELDS_1;

//     NFIELDS: coverpoint ins.current.insn[31:29] {
//         bins one    = {3'b000};
//         bins two    = {3'b001};
//         bins three  = {3'b010};
//         bins four   = {3'b011};
//         bins five   = {3'b100};
//         bins six    = {3'b101};
//         bins seven  = {3'b110};
//         bins eight  = {3'b111};
//     }

//     vtype_csr_lmul: coverpoint 3'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul")) {
//         `ifdef LMUL_F8_SUPPORTED
//             bins f8 = {3'b101};
//         `endif
//         `ifdef LMUL_F4_SUPPORTED
//             bins f4 = {3'b110};
//         `endif
//         `ifdef LMUL_F2_SUPPORTED
//             bins f2 = {3'b111};
//         `endif
//         bins one    = {3'b000};
//         bins two    = {3'b001};
//         bins four   = {3'b010};
//         bins eight  = {3'b011};

//         bins random_legal = {3'b000, 3'b001, 3'b010, 3'b011
//         `ifdef LMUL_F8_SUPPORTED
//             ,3'b101
//         `endif
//         `ifdef LMUL_F4_SUPPORTED
//             ,3'b110
//         `endif
//         `ifdef LMUL_F2_SUPPORTED
//             ,3'b111
//         `endif
//         };
//     }

//     vtype_csr_sew: coverpoint 3'(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")) {
//         bins eight  = {3'b000};
//         bins sixteen = {3'b001};
//         bins thirtytwo = {3'b010};
//         bins sixtyfour = {3'b011};
//     }


//     cr_vector_load_sew_lmul_nfields: cross vector_load, vtype_csr_sew, vtype_csr_lmul, NFIELDS, vd_reg_div_8, vtype_prev_vill_clear;


// endgroup

function void ssstrictv_sample(int hart, int issue, ins_t ins);
    SsstrictV_vcsr_cg.sample(ins);
    SsstrictV_instr_cg.sample(ins);
endfunction
