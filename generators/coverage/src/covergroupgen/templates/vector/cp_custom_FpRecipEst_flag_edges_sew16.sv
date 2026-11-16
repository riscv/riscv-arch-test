    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FpRecipEst_flag_edges
    //////////////////////////////////////////////////////////////////////////////////

    fp_flags_clear : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_FCSR, "fflags")[4:0] {
            bins clear = {0};
    }

    vs2_0_recip7_sign : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[15] {
            bins pos = {0};
            bins neg = {1};
    }

    vs2_0_recip7_exp : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[14:10] {
            bins zero        = {0};  // zero or subnormal
            bins one         = {1};  // 2^(-B+1) ≤ |x| < 2^(-B+2), smallest normal exponent
            bins bias        = {15}; // 1 ≤ |x| < 2
            bins two_bias_m2 = {28}; // 2^(B-2) ≤ |x| < 2^(B-1), largest exponent with a normal result
            bins two_bias_m1 = {29}; // 2^(B-1) ≤ |x| < 2^B, subnormal result with sig=1x
            bins two_bias    = {30}; // 2^B ≤ |x| < 2^(B+1), subnormal result with sig=01
            bins ones        = {31}; // inf or NaN
    }

    vs2_0_recip7_frac : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[9:0] {
            bins zero      = {10'h000};
            bins lsb       = {10'h001};
            bins sig00_max = {10'h0FF};
            bins sig01_min = {10'h100};
            bins sig01_max = {10'h1FF};
            bins sig1x_min = {10'h200};
            bins ones      = {10'h3FF};
    }

    cp_custom_FpRecipEst_flag_edges: cross std_vec, fp_flags_clear, cp_csr_frm_v, vs2_0_recip7_sign, vs2_0_recip7_exp, vs2_0_recip7_frac;

    //// end cp_custom_FpRecipEst_flag_edges////////////////////////////////////////////////
