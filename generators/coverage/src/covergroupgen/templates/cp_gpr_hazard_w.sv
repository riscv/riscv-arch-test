    cp_gpr_hazard_w : coverpoint (
        (check_gpr_hazards(ins.hart, ins.issue, 0) == WAW_HAZARD) ? 1 : 0
    ) iff (ins.trap == 0) {
        bins waw_depth0 = {1};
    }
