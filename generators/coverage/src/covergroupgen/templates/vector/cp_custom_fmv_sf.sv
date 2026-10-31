    // //////////////////////////////////////////////////////////////////////////////////////////////////////////
    // cp_custom_fmv_sf
    // //////////////////////////////////////////////////////////////////////////////////////////////////////////

    // Scalar write ignores LMUL: vd can be any register at any LMUL
    vd_all_regs: coverpoint ins.current.insn[11:7] {
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

    cp_custom_fmv_sf_vd_all_lmul: cross std_vec, vd_all_regs, vtype_all_lmul;

//// end cp_custom_fmv_sf ///////////////////////////////////////////////////////////////////////////
