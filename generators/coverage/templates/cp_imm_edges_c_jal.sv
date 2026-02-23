    cp_imm_edges_c_jal : coverpoint signed'(ins.current.imm)  iff (ins.trap == 0 )  {
        // imm is the jump offset
        // Adding a range to account for signature logic (32 bytes)
        bins b_2     = {2};
        bins b_4     = {4};
        bins b_8     = {8};
        bins b_16    = {16};
        bins b_32    = {32};
        bins b_64    = {64};
        bins b_128   = {[96:128]};
        bins b_256   = {[224:256]};
        bins b_512   = {[480:512]};
        bins b_1024  = {[992:1024]};
        bins b_m2    = {-2};
        bins b_m4    = {-4};
        bins b_m8    = {-8};
        bins b_m16   = {-16};
        bins b_m32   = {[-32:-60]};
        bins b_m64   = {[-64:-96]};
        bins b_m128  = {[-128:-160]};
        bins b_m256  = {[-256:-288]};
        bins b_m512  = {[-512:-544]};
        bins b_m1024 = {[-1024:-1056]};
        bins b_m2048 = {-2048};
    }
