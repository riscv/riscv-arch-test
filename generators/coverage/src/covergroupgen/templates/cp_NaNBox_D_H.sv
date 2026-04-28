    cp_NaNBox_D_H : coverpoint unsigned'(ins.current.fd_val[63:16])  iff (ins.trap == 0 )  {
        // NaNBoxing (half result in a double register)
        bins NaNBox = {48'hffffffffffff};
    }
