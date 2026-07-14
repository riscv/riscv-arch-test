    cp_gpr_hazard_rw : coverpoint (
        (check_gpr_hazards(ins.hart, ins.issue, 0) == RAW_HAZARD) ? 1 :
        (check_gpr_hazards(ins.hart, ins.issue, 0) == WAW_HAZARD) ? 3 :
        (check_gpr_hazards(ins.hart, ins.issue, 1) == RAW_HAZARD) ? 2 : 0
    ) iff (ins.trap == 0) {
        bins no_hazard       = {0};
        bins raw_rs_depth0   = {1};  // covers rs1 and rs2 RAW at depth=0
        bins raw_rs_depth1   = {2};  // covers rs1 and rs2 RAW at depth=1
        bins waw_depth0      = {3};
    }
