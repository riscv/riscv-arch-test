    //////////////////////////////////////////////////////////////////////////////////
    // cr_vs2_vd_edges_egs4_subbytes_sm
    //////////////////////////////////////////////////////////////////////////////////

    // Cross coverage of VS2 edges and VD SM4 subbyte edges (EGS=4, B = x1^x2^x3^rk0)
    cr_vs2_vd_edges_egs4_subbytes_sm_0 : cross cp_vs2_edges_egs4, cp_vd_edges_egs4_sm_byte_0  iff (ins.trap == 0 )  {}
    cr_vs2_vd_edges_egs4_subbytes_sm_1 : cross cp_vs2_edges_egs4, cp_vd_edges_egs4_sm_byte_1  iff (ins.trap == 0 )  {}
    cr_vs2_vd_edges_egs4_subbytes_sm_2 : cross cp_vs2_edges_egs4, cp_vd_edges_egs4_sm_byte_2  iff (ins.trap == 0 )  {}
    cr_vs2_vd_edges_egs4_subbytes_sm_3 : cross cp_vs2_edges_egs4, cp_vd_edges_egs4_sm_byte_3  iff (ins.trap == 0 )  {}

    //// end cr_vs2_vd_edges_egs4_subbytes_sm ////////////////////////////////////////////////
