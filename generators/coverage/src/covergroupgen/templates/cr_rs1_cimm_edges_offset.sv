    cp_imm_edges_5bit_u_n0 : coverpoint signed'(ins.current.cimm)  iff (ins.trap == 0 )  {
        // Zibi cimm edge values. The 5-bit cimm field decodes to a signed
        // comparison constant: field 0 encodes -1, fields 1..31 encode 1..31.
        bins b_0 = {-1}; // cimm field 0 encodes the value -1
        bins b_1 = {1};
        bins b_2 = {2};
        bins b_3 = {3};
        bins b_4 = {4};
        bins b_8 = {8};
        bins b_16 = {16};
        bins b_30 = {30};
        bins b_31 = {31};
    }
    cr_rs1_cimm_edges_offset : cross cp_rs1_edges,cp_imm_edges_5bit_u_n0,cp_offset  iff (ins.trap == 0 )  {
        // Cross coverage of RS1 edges and cimm edges and branch direction
    }
