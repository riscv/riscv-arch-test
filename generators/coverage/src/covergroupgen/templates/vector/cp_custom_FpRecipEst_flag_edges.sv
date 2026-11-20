    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_FpRecipEst_flag_edges
    //////////////////////////////////////////////////////////////////////////////////

    // Crosses sign, exponent field, fraction and frm of vs2 element 0 so that every row of the
    // spec's vfrec7 table is hit, with values on both sides of each row boundary. B is the
    // exponent bias. With exponent field 0, the fraction bins select ±0 and the subnormal rows
    // with sig=00, sig=01 and sig=1x.
`ifdef COVER_VFCUSTOM16
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
`elsif COVER_VFCUSTOM32
    fp_flags_clear : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_FCSR, "fflags")[4:0] {
            bins clear = {0};
    }

    vs2_0_recip7_sign : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[31] {
            bins pos = {0};
            bins neg = {1};
    }

    vs2_0_recip7_exp : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[30:23] {
            bins zero        = {0};   // zero or subnormal
            bins one         = {1};   // 2^(-B+1) ≤ |x| < 2^(-B+2), smallest normal exponent
            bins bias        = {127}; // 1 ≤ |x| < 2
            bins two_bias_m2 = {252}; // 2^(B-2) ≤ |x| < 2^(B-1), largest exponent with a normal result
            bins two_bias_m1 = {253}; // 2^(B-1) ≤ |x| < 2^B, subnormal result with sig=1x
            bins two_bias    = {254}; // 2^B ≤ |x| < 2^(B+1), subnormal result with sig=01
            bins ones        = {255}; // inf or NaN
    }

    vs2_0_recip7_frac : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[22:0] {
            bins zero      = {23'h00_0000};
            bins lsb       = {23'h00_0001};
            bins sig00_max = {23'h1F_FFFF};
            bins sig01_min = {23'h20_0000};
            bins sig01_max = {23'h3F_FFFF};
            bins sig1x_min = {23'h40_0000};
            bins ones      = {23'h7F_FFFF};
    }

    cp_custom_FpRecipEst_flag_edges: cross std_vec, fp_flags_clear, cp_csr_frm_v, vs2_0_recip7_sign, vs2_0_recip7_exp, vs2_0_recip7_frac;
`elsif COVER_VFCUSTOM64
    `ifdef D_SUPPORTED
    fp_flags_clear : coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_FCSR, "fflags")[4:0] {
            bins clear = {0};
    }

    vs2_0_recip7_sign : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[63] {
            bins pos = {0};
            bins neg = {1};
    }

    vs2_0_recip7_exp : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[62:52] {
            bins zero        = {0};    // zero or subnormal
            bins one         = {1};    // 2^(-B+1) ≤ |x| < 2^(-B+2), smallest normal exponent
            bins bias        = {1023}; // 1 ≤ |x| < 2
            bins two_bias_m2 = {2044}; // 2^(B-2) ≤ |x| < 2^(B-1), largest exponent with a normal result
            bins two_bias_m1 = {2045}; // 2^(B-1) ≤ |x| < 2^B, subnormal result with sig=1x
            bins two_bias    = {2046}; // 2^B ≤ |x| < 2^(B+1), subnormal result with sig=01
            bins ones        = {2047}; // inf or NaN
    }

    vs2_0_recip7_frac : coverpoint get_vr_element_zero(ins.hart, ins.issue, ins.current.vs2_val)[51:0] {
            bins zero      = {52'h0_0000_0000_0000};
            bins lsb       = {52'h0_0000_0000_0001};
            bins sig00_max = {52'h3_FFFF_FFFF_FFFF};
            bins sig01_min = {52'h4_0000_0000_0000};
            bins sig01_max = {52'h7_FFFF_FFFF_FFFF};
            bins sig1x_min = {52'h8_0000_0000_0000};
            bins ones      = {52'hF_FFFF_FFFF_FFFF};
    }

    cp_custom_FpRecipEst_flag_edges: cross std_vec, fp_flags_clear, cp_csr_frm_v, vs2_0_recip7_sign, vs2_0_recip7_exp, vs2_0_recip7_frac;
    `endif
`endif

    //// end cp_custom_FpRecipEst_flag_edges////////////////////////////////////////////////
