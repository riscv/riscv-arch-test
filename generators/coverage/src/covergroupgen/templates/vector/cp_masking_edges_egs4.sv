    cp_masking_edges_egs4 : coverpoint mask_edges_check(ins.hart, ins.issue, ins.prev.v_wdata[0])  iff (ins.trap == 0 & ins.current.vm == 0)  {
        // Edge values of v0 (vector mask register) for EGS=4 instructions
        bins zero           = {mask_zero            };
        bins ones           = {mask_ones            };
        bins vlmaxm1ones    = {mask_vlmaxm1ones     };
        bins vlmaxd2p1ones  = {mask_vlmaxd2p1ones   };
        bins random         = {mask_random          };
    }
