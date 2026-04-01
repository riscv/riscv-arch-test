// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_custom_fmv_fs_vs2_all_lmul
// //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Scalar read ignores LMUL: vs2 can be any register at any LMUL
    // Two independent crosses avoid combinatorial explosion (32×N vs 32+N bins)

    vs2_all_regs: coverpoint ins.current.insn[24:20] {
        bins registers[] = {[0:31]};
    }

`ifndef COVER_VFCUSTOM64
    vtype_all_lmul: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        `ifdef COVER_VFCUSTOM16
            `ifdef LMULf4_SUPPORTED
                bins fourth = {6};
            `endif
        `endif
        `ifdef LMULf2_SUPPORTED
            bins half   = {7};
        `endif
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    cp_custom_fmv_fs_vs2_all_lmul_regs: cross std_vec, vs2_all_regs;
    cp_custom_fmv_fs_vs2_all_lmul_lmuls: cross std_vec, vtype_all_lmul;
`else
    `ifdef FLEN64
    vtype_all_lmul: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    cp_custom_fmv_fs_vs2_all_lmul_regs: cross std_vec, vs2_all_regs;
    cp_custom_fmv_fs_vs2_all_lmul_lmuls: cross std_vec, vtype_all_lmul;
    `endif
`endif

//// end cp_custom_fmv_fs_vs2_all_lmul ///////////////////////////////////////////////////////////////////////////
