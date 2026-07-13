// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_widen_max_sew
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Widening at MAX_SEW: destination EEW = 2*SEW > ELEN, must trap
    // Covers all widening instructions (including widening reductions)
    // Tests all legal widening LMUL values (1-4) crossed with all supported SEWs

    vtype_lmul_widen: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one  = {0};
        bins two  = {1};
        bins four = {2};
    }


    cp_ssstrictv_widen_max_sew: cross std_trap_vec, vtype_all_sew_supported, vtype_lmul_widen {
        // Only SEW=ELEN_max (sixtyfour) yields dest EEW > ELEN at any LMUL≥1;
        // smaller SEWs do not violate the encoding so std_trap_vec * (sew_8/16/32, lmul_*) is unreachable.
        ignore_bins below_max_sew = binsof(vtype_all_sew_supported) intersect {0, 1, 2};
    }

//// end cp_ssstrictv_widen_max_sew /////////////////////////////////////////////////////////////////////////
