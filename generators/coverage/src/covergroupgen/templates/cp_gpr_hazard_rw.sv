    cp_gpr_hazard_rw : coverpoint (
        (check_gpr_hazards(ins.hart, ins.issue, 0) == RAW_HAZARD && check_gpr_hazard_field(ins.hart, ins.issue, 0) == HAZARD_FIELD_RS1) ? 1 :
        (check_gpr_hazards(ins.hart, ins.issue, 0) == RAW_HAZARD && check_gpr_hazard_field(ins.hart, ins.issue, 0) == HAZARD_FIELD_RS2) ? 2 :
        (check_gpr_hazards(ins.hart, ins.issue, 0) == WAW_HAZARD) ? 5 :
        (check_gpr_hazards(ins.hart, ins.issue, 1) == RAW_HAZARD && check_gpr_hazard_field(ins.hart, ins.issue, 1) == HAZARD_FIELD_RS1) ? 3 :
        (check_gpr_hazards(ins.hart, ins.issue, 1) == RAW_HAZARD && check_gpr_hazard_field(ins.hart, ins.issue, 1) == HAZARD_FIELD_RS2) ? 4 : 0
    ) iff (ins.trap == 0) {
        bins no_hazard      = {0};
        bins raw_rs1_depth0 = {1};
        bins raw_rs2_depth0 = {2};
        bins raw_rs1_depth1 = {3};
        bins raw_rs2_depth1 = {4};
        bins waw_depth0     = {5};
    }