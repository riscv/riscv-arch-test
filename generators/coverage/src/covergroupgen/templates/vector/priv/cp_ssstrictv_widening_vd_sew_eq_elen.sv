// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_widening_vd_sew_eq_elen
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Widening with SEW=ELEN: destination EEW = 2*SEW > ELEN, must trap
    // LMUL=1, registers chosen to avoid overlap traps (vd=8, vs2=10, vs1=12)

    vtype_lmul_1_4b6be4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one = {0};
    }


    cp_ssstrictv_widening_vd_sew_eq_elen: cross std_trap_vec, vtype_all_sew_supported, vtype_lmul_1_4b6be4 {
        // Only SEW=ELEN_max yields dest EEW > ELEN; smaller SEWs at LMUL=1 do not
        // exceed ELEN so the cross is unreachable for those bins.
        ignore_bins below_max_sew = binsof(vtype_all_sew_supported) intersect {0, 1, 2};
    }

//// end cp_ssstrictv_widening_vd_sew_eq_elen ////////////////////////////////////////////////////////////////
