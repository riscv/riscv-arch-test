    cp_gpr_hazard_r : coverpoint (
        (check_gpr_hazards(ins.hart, ins.issue, 0) == RAW_HAZARD) ? 1 :
        (check_gpr_hazards(ins.hart, ins.issue, 1) == RAW_HAZARD) ? 2 : 0
    ) iff (ins.trap == 0) {
        bins no_hazard  = {0};
        bins raw_depth0 = {1};
        bins raw_depth1 = {2};
    }
