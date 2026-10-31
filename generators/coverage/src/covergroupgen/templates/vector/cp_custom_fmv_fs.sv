    // //////////////////////////////////////////////////////////////////////////////////////////////////////////
    // cp_custom_fmv_fs
    // //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Scalar read ignores LMUL: vs2 can be any register at any LMUL
    vs2_all_regs: coverpoint ins.current.insn[24:20] {
        bins reg[] = {[0:31]};
    }

    vtype_all_lmul: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        // Fractional LMULs gated by SEW: LMUL >= SEW/ELEN required
        // mf8 never valid for FP (SEW >= 16, needs SEW <= 8)
        `ifdef COVER_VFCUSTOM16
            `ifdef UDB_ELEN_64
                bins fourth = {6};
            `endif
            bins half   = {7};
        `endif
        `ifdef COVER_VFCUSTOM32
            `ifdef UDB_ELEN_64
                bins half   = {7};
            `endif
        `endif
        bins one    = {0};
        bins two    = {1};
        bins four   = {2};
        bins eight  = {3};
    }

    cp_custom_fmv_fs_vs2_all_lmul: cross std_vec, vs2_all_regs, vtype_all_lmul;

//// end cp_custom_fmv_fs ///////////////////////////////////////////////////////////////////////////
