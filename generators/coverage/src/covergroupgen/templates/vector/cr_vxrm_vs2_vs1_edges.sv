//////////////////////////////////////////////////////////////////////////////////
    // cr_vxrm_vs2_vs1_edges
    //////////////////////////////////////////////////////////////////////////////////

    cp_csr_vxrm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vcsr", "vxrm")  iff (ins.trap == 0)  {
        // Value of VCSR.vxrm (vector fixed-point rounding mode)
        bins rnu  = {2'b00};
        bins rne  = {2'b01};
        bins rdn  = {2'b10};
        bins rod  = {2'b11};
    }

    cr_vxrm_vs2_vs1_edges : cross cp_vs2_edges,cp_vs1_edges,cp_csr_vxrm  iff (ins.trap == 0 )  {
        // Cross coverage VS2, VS1, rounding mode
    }

    //// end cr_vxrm_vs2_vs1_edges////////////////////////////////////////////////
