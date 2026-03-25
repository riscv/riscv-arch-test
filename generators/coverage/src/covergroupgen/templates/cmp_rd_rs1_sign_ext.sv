    cmp_rd_rs1_sign_ext : coverpoint (ins.current.rd_val[63:32] == {32{ins.current.rd_val[31]}}) iff (ins.trap == 0) {
        // Compare cases where rd is the sign-extended version of rs1
        bins sign_ext_match = {1};  // Cases where rd is the sign-extended version of rs1
    }  
    