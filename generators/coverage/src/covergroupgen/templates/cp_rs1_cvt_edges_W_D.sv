    cp_rs1_cvt_edges_W_D : coverpoint unsigned'(ins.current.rs1_val[31:0])  iff (ins.trap == 0 )  {
        // RS1 INT32_MIN and INT32_MAX
        bins min                      = {32'h80000000};
        bins max                      = {32'h7fffffff};
    }
