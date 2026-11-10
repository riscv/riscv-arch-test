    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vreductionw_vd_vs1_emul_16
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector widening reduction operations
    // Tests that widening reductions at LMUL=8 do NOT trap even though EMUL would
    // be 16, because reduction scalar destinations use EMUL=1 per V spec §13.3.

    // Self-contained validity: vill clear, vstart=0, vl>0, no trap
    vreductionw_valid: coverpoint {get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vill") == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VSTART) == 0 &
                        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VL) != 0 &
                        ins.trap == 0
                    }
    {
        bins true = {1'b1};
    }

    // LMUL=8 (vlmul encoding = 3)
    vreductionw_lmul_8: coverpoint get_csr_field(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_VTYPE, "vlmul") {
        bins eight = {3};
    }

    cp_custom_vreductionw_vd_vs1_emul_16 :      cross vreductionw_valid, vreductionw_lmul_8;

    //// end cp_custom_vreductionw_vd_vs1_emul_16 ////////////////////////////////////////////////
