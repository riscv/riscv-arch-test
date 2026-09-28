    // aes64ks1i applies SubBytes to rs1[63:32]; the test replicates the sbox input into every
    // byte, so sample the low byte of that word.
    cp_sbox_rs1 : coverpoint unsigned'(ins.current.rs1_val[39:32])  iff (ins.trap == 0 )  {
        // exercise all 256 values into the sbox
        bins all[] = {[0:$]};
    }
