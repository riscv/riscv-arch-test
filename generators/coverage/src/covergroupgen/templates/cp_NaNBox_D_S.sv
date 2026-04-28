    cp_NaNBox_D_S : coverpoint unsigned'(ins.current.fd_val[63:32])  iff (ins.trap == 0 )  {
        // NaNBoxing (float result in a double register)
        bins NaNBox = {32'hffffffff};
    }
