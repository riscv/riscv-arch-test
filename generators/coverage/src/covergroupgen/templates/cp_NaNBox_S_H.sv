    cp_NaNBox_S_H : coverpoint unsigned'(ins.current.fd_val[31:16])  iff (ins.trap == 0 )  {
        // NaNBoxing (half result in a float register)
        bins NaNBox = {16'hffff};
    }
