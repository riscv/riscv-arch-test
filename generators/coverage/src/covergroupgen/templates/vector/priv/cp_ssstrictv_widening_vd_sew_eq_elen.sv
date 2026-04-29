// //////////////////////////////////////////////////////////////////////////////////////////////////////////
// cp_ssstrictv_widening_vd_sew_eq_elen
// //////////////////////////////////////////////////////////////////////////////////////////////////////////


    // Widening with SEW=ELEN: destination EEW = 2*SEW > ELEN, must trap
    // LMUL=1, registers chosen to avoid overlap traps (vd=8, vs2=10, vs1=12)

    vtype_lmul_1_4b6be4: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vtype", "vlmul") {
        bins one = {0};
    }

    trap_occurred_4b6be4: coverpoint ins.trap {
        bins trapped = {1'b1};
    }

    cp_ssstrictv_widening_vd_sew_eq_elen: cross std_trap_vec, vtype_all_sew_supported, vtype_lmul_1_4b6be4, trap_occurred_4b6be4;

//// end cp_ssstrictv_widening_vd_sew_eq_elen ////////////////////////////////////////////////////////////////
