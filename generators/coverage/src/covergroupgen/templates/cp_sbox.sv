    cp_sbox : coverpoint unsigned'(ins.current.rs2_val[7:0])  iff (ins.trap == 0 )  {
        // exercise all 256 values into the sbox
        bins all[] = {[0:$]};
    }
