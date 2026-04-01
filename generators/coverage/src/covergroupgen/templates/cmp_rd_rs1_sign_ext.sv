    cmp_rd_rs1_sign_ext : coverpoint (ins.current.rd_val == $signed(ins.current.rd_val[31:0])) iff (ins.trap == 0) {
        // Compare cases where rd is the sign-extended version of rs1
        bins rd_sign_ext__value_match = {1};  // Cases where rd is the sign-extended version of rs1
    }
