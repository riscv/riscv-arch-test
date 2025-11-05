///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Standard Covergroups
//
// Written: James Kaden Cassidy jacassidy@hmc.edu 3 June 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

//TODO many of these coverpoints are unnecessary for most instructions thus this document should be separated into categories
// that way coverpoints are only imported when needed TODO

    //Common custom vector coverpoints
    //included at the top of every custom vector covergroup

    //////////////////////////////////////////////////////////////////////////////////
    // Standard vector coverpoints
    //////////////////////////////////////////////////////////////////////////////////

    vtype_prev_vill_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins vill_not_set = {0};
    }

    vtype_prev_vill_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vill") {
        bins vill_set = {1};
    }

    vstart_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstart", "vstart") {
        bins target = {0};
    }

    vl_nonzero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") {
        //Any value between max and 1
        bins target = {[`XLEN'h10000:`XLEN'h1]};
    }

    mask_enabled: coverpoint ins.current.insn[25] {
        bins enabled = {1'b0};
    }

    vd_v0: coverpoint ins.current.insn[11:7] {
        bins zero = {5'b00000};
    }

    no_trap: coverpoint (ins.trap == 0) {
        bins true = {1'b1};
    }

    // ensures vd updates
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

    vd_all_reg : coverpoint ins.current.insn[11:7] {
        // All vector destination registers
    }

    vs1_all_reg : coverpoint ins.current.insn[19:15] {
        // All vs1 registers
    }

    vs2_all_reg : coverpoint ins.current.insn[24:20] {
        // All vs2 registers
    }

    vd_eq_vs1 : coverpoint (ins.current.insn[11:7] == ins.current.insn[19:15]) {
        bins target = {1'b1};
    }

    vd_eq_vs2 : coverpoint (ins.current.insn[11:7] == ins.current.insn[24:20]) {
        bins target = {1'b1};
    }

    vs2_eq_vs1 : coverpoint (ins.current.insn[19:15] == ins.current.insn[24:20]) {
        bins target = {1'b1};
    }

    vd_ne_vs2 : coverpoint (ins.current.insn[24:20] != ins.current.insn[11:7]) {
        bins target = {1'b1};
    }

    vd_ne_vs1 : coverpoint (ins.current.insn[19:15] != ins.current.insn[11:7]) {
        bins target = {1'b1};
    }

    vs2_ne_vs1 : coverpoint (ins.current.insn[19:15] != ins.current.insn[24:20]) {
        bins target = {1'b1};
    }

    vl_max: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl")
                        == get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
        bins target = {1'b1};
    }

    vl_not_max: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vl", "vl") ==
                            get_vtype_vlmax(ins.hart, ins.issue, `SAMPLE_BEFORE)) {
        bins target = {1'b0};
    }

    vtype_all_lmulge1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    vtype_all_lmul_supported_sew8 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        `ifdef LMULf8_SUPPORTED
        bins eighth  = {5};
        `endif
        `ifdef LMULf4_SUPPORTED
        bins fourth = {6};
        `endif
        `ifdef LMULf2_SUPPORTED
        bins half   = {7};
        `endif
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    vtype_all_lmul_supported_sew16 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        `ifdef LMULf4_SUPPORTED
        bins fourth = {6};
        `endif
        `ifdef LMULf2_SUPPORTED
        bins half   = {7};
        `endif
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    vtype_all_lmul_supported_sew32 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        `ifdef LMULf2_SUPPORTED
        bins half   = {7};
        `endif
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    vtype_all_lmul_supported_sew64 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    vtype_lmul_1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one = {0};
    }

    vtype_lmul_2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {1};
    }

    vtype_lmul_4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {2};
    }

    vtype_lmul_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two = {3};
    }

    vtype_all_lmulgt1: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    vtype_all_sewgt8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        `ifdef SEW16_SUPPORTED
        bins sixteen    = {1};
        `endif
        `ifdef SEW32_SUPPORTED
        bins thirtytwo  = {2};
        `endif
        `ifdef SEW64_SUPPORTED
        bins sixtyfour  = {3};
        `endif
    }

    vtype_sew_8: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        `ifdef SEW8_SUPPORTED
        bins eight = {0};
        `endif
    }

    vtype_sew_16: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        `ifdef SEW16_SUPPORTED
        bins sixteen = {1};
        `endif
    }

    vtype_sew_32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        `ifdef SEW32_SUPPORTED
        bins thirtytwo = {2};
        `endif
    }

    vtype_sew_64: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        `ifdef SEW64_SUPPORTED
        bins sixtyfour = {3};
        `endif
    }

    vtype_all_sew_supported: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew") {
        `ifdef SEW8_SUPPORTED
        bins eight      = {0};
        `endif
        `ifdef SEW16_SUPPORTED
        bins sixteen    = {1};
        `endif
        `ifdef SEW32_SUPPORTED
        bins thirtytwo  = {2};
        `endif
        `ifdef SEW64_SUPPORTED
        bins sixtyfour  = {3};
        `endif
    }

    vtype_sew_supported : coverpoint check_vtype_sew_supported(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vsew")) {
        bins supported = {1};
    }

    //////////////////////////////////////////////////////////////////////////////////
    // Vector csr common coverpoints
    //////////////////////////////////////////////////////////////////////////////////

    misa_v_active : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "misa", "exts")[21] {
        bins vector = {1};
    }

    //////////////////////////////////////////////////////////////////////////////////
    // Vector register groups coverpoints
    // all_reg_aligned: every register that is a multiple of lmul
    // all_reg_unaligned: every register that is not a multiple of lmul
    // reg_aligned: any register that is a multiple of lmul
    // overlap: make sure register groups overlap at a specific lmul
    // no_overlap: make sure register groups do not overlap at a specific lmul
    //////////////////////////////////////////////////////////////////////////////////

    vd_all_reg_aligned_lmul_2: coverpoint ins.current.insn[11:7] {
        wildcard ignore_bins odd = {5'b????1};
    }

    vd_all_reg_aligned_lmul_4: coverpoint ins.current.insn[11:7] {
        wildcard ignore_bins end_1 = {5'b???01};
        wildcard ignore_bins end_2 = {5'b???10};
        wildcard ignore_bins end_3 = {5'b???11};
    }

    vd_all_reg_aligned_lmul_8: coverpoint ins.current.insn[11:7] {
        wildcard ignore_bins end_1 = {5'b??001};
        wildcard ignore_bins end_2 = {5'b??010};
        wildcard ignore_bins end_3 = {5'b??011};
        wildcard ignore_bins end_4 = {5'b??101};
        wildcard ignore_bins end_5 = {5'b??110};
        wildcard ignore_bins end_6 = {5'b??111};
        wildcard ignore_bins end_7 = {5'b??100};
    }

    vs1_all_reg_aligned_lmul_2: coverpoint ins.current.insn[19:15] {
        wildcard ignore_bins odd = {5'b????1};
    }

    vs1_all_reg_aligned_lmul_4: coverpoint ins.current.insn[19:15] {
        wildcard ignore_bins end_1 = {5'b???01};
        wildcard ignore_bins end_2 = {5'b???10};
        wildcard ignore_bins end_3 = {5'b???11};
    }

    vs1_all_reg_aligned_lmul_8: coverpoint ins.current.insn[19:15] {
        wildcard ignore_bins end_1 = {5'b??001};
        wildcard ignore_bins end_2 = {5'b??010};
        wildcard ignore_bins end_3 = {5'b??011};
        wildcard ignore_bins end_4 = {5'b??101};
        wildcard ignore_bins end_5 = {5'b??110};
        wildcard ignore_bins end_6 = {5'b??111};
        wildcard ignore_bins end_7 = {5'b??100};
    }

    vd_all_reg_unaligned_lmul_2: coverpoint ins.current.insn[11:7] {
        wildcard ignore_bins divisible_by_2 = {5'b????0};
    }

    vd_all_reg_unaligned_lmul_4: coverpoint ins.current.insn[11:7] {
        wildcard ignore_bins divisible_by_4 = {5'b???00};
    }

    vd_all_reg_unaligned_lmul_8: coverpoint ins.current.insn[11:7] {
        wildcard ignore_bins divisible_by_8 = {5'b??000};
    }

    vs1_all_reg_unaligned_lmul_2: coverpoint ins.current.insn[19:15] {
        wildcard ignore_bins divisible_by_2 = {5'b????0};
    }

    vs1_all_reg_unaligned_lmul_4: coverpoint ins.current.insn[19:15] {
        wildcard ignore_bins divisible_by_4 = {5'b???00};
    }

    vs1_all_reg_unaligned_lmul_8: coverpoint ins.current.insn[19:15] {
        wildcard ignore_bins divisible_by_8 = {5'b??000};
    }

    vs2_all_reg_unaligned_lmul_2: coverpoint ins.current.insn[24:20] {
        wildcard ignore_bins divisible_by_2 = {5'b????0};
    }

    vs2_all_reg_unaligned_lmul_4: coverpoint ins.current.insn[24:20] {
        wildcard ignore_bins divisible_by_4 = {5'b???00};
    }

    vs2_all_reg_unaligned_lmul_8: coverpoint ins.current.insn[24:20] {
        wildcard ignore_bins divisible_by_8 = {5'b??000};
    }

    vs2_reg_aligned_lmul_2: coverpoint ins.current.insn[24:20] {
        wildcard bins divisible_by_2 = {5'b????0};
    }

    vs2_reg_aligned_lmul_4: coverpoint ins.current.insn[24:20] {
        wildcard bins divisible_by_4 = {5'b???00};
    }

    vs2_reg_aligned_lmul_8: coverpoint ins.current.insn[24:20] {
        wildcard bins divisible_by_8 = {5'b??000};
    }

    vs1_reg_aligned_lmul_2: coverpoint ins.current.insn[19:15] {
        wildcard bins divisible_by_2 = {5'b????0};
    }

    vs1_reg_aligned_lmul_4: coverpoint ins.current.insn[19:15] {
        wildcard bins divisible_by_4 = {5'b???00};
    }

    vs1_reg_aligned_lmul_8: coverpoint ins.current.insn[19:15] {
        wildcard bins divisible_by_8 = {5'b??000};
    }

    vd_reg_aligned_lmul_2: coverpoint ins.current.insn[11:7] {
        wildcard bins divisible_by_2 = {5'b????0};
    }

    vd_reg_aligned_lmul_4: coverpoint ins.current.insn[11:7] {
        wildcard bins divisible_by_4 = {5'b???00};
    }

    vd_reg_aligned_lmul_8: coverpoint ins.current.insn[11:7] {
        wildcard bins divisible_by_8 = {5'b??000};
    }

    vs2_reg_unaligned_lmul_2: coverpoint ins.current.insn[24:20] {
        wildcard bins odd = {5'b????1};
    }

    vs2_reg_unaligned_lmul_4: coverpoint ins.current.insn[24:20] {
        wildcard bins range = {[5'b???01: 5'b???11]};
    }

    vs2_reg_unaligned_lmul_8: coverpoint ins.current.insn[24:20] {
        wildcard bins range = {[5'b??001: 5'b??111]};
    }

    vs1_reg_unaligned_lmul_2: coverpoint ins.current.insn[19:15] {
        wildcard bins odd = {5'b????1};
    }

    vs1_reg_unaligned_lmul_4: coverpoint ins.current.insn[19:15] {
        wildcard bins range = {[5'b???01: 5'b???11]};
    }

    vs1_reg_unaligned_lmul_8: coverpoint ins.current.insn[19:15] {
        wildcard bins range = {[5'b??001: 5'b??111]};
    }

    vd_reg_unaligned_lmul_2: coverpoint ins.current.insn[11:7] {
        wildcard bins odd = {5'b????1};
    }

    vd_reg_unaligned_lmul_4: coverpoint ins.current.insn[11:7] {
        wildcard bins range = {[5'b???01: 5'b???11]};
    }

    vd_reg_unaligned_lmul_8: coverpoint ins.current.insn[11:7] {
        wildcard bins range = {[5'b??001: 5'b??111]};
    }

    vs2_vd_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) {
        bins overlapping = {1'b1};
    }

    vs1_vd_overlap_lmul1: coverpoint (ins.current.insn[19:16] == ins.current.insn[11:8]) {
        bins overlapping = {1'b1};
    }

    vs1_vd_overlap_lmul2: coverpoint (ins.current.insn[19:17] == ins.current.insn[11:9]) {
        bins overlapping = {1'b1};
    }

    vs2_vd_overlap_lmul2: coverpoint (ins.current.insn[24:22] == ins.current.insn[11:9]) {
        bins overlapping = {1'b1};
    }

    vs1_vd_overlap_lmul4: coverpoint (ins.current.insn[19:18] == ins.current.insn[11:10]) {
        bins overlapping = {1'b1};
    }

    vs2_vd_overlap_lmul4: coverpoint (ins.current.insn[24:23] == ins.current.insn[11:10]) {
        bins overlapping = {1'b1};
    }

    vs1_vd_no_overlap_lmul1: coverpoint (ins.current.insn[19:16] == ins.current.insn[11:8]) {
        bins overlapping = {1'b0};
    }

    vs2_vd_no_overlap_lmul1: coverpoint (ins.current.insn[24:21] == ins.current.insn[11:8]) {
        bins overlapping = {1'b0};
    }

    vs1_vd_no_overlap_lmul2: coverpoint (ins.current.insn[19:17] == ins.current.insn[11:9]) {
        bins overlapping = {1'b0};
    }

    vs2_vd_no_overlap_lmul2: coverpoint (ins.current.insn[24:22] == ins.current.insn[11:9]) {
        bins overlapping = {1'b0};
    }

    vs1_vd_no_overlap_lmul4: coverpoint (ins.current.insn[19:18] == ins.current.insn[11:10]) {
        bins overlapping = {1'b0};
    }

    vs2_vd_no_overlap_lmul4: coverpoint (ins.current.insn[24:23] == ins.current.insn[11:10]) {
        bins overlapping = {1'b0};
    }
