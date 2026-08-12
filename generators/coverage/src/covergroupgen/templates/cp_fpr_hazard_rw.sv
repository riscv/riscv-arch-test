    cp_fpr_hazard_rw : coverpoint (
        (check_fpr_hazards(ins.hart, ins.issue, 0) == RAW_HAZARD && check_fpr_hazard_field(ins.hart, ins.issue, 0) == HAZARD_FIELD_RS1) ? 1 :
        (check_fpr_hazards(ins.hart, ins.issue, 0) == RAW_HAZARD && check_fpr_hazard_field(ins.hart, ins.issue, 0) == HAZARD_FIELD_RS2) ? 2 :
        (check_fpr_hazards(ins.hart, ins.issue, 0) == RAW_HAZARD && check_fpr_hazard_field(ins.hart, ins.issue, 0) == HAZARD_FIELD_RS3) ? 3 :
        (check_fpr_hazards(ins.hart, ins.issue, 0) == WAW_HAZARD) ? 7 :
        (check_fpr_hazards(ins.hart, ins.issue, 1) == RAW_HAZARD && check_fpr_hazard_field(ins.hart, ins.issue, 1) == HAZARD_FIELD_RS1) ? 4 :
        (check_fpr_hazards(ins.hart, ins.issue, 1) == RAW_HAZARD && check_fpr_hazard_field(ins.hart, ins.issue, 1) == HAZARD_FIELD_RS2) ? 5 :
        (check_fpr_hazards(ins.hart, ins.issue, 1) == RAW_HAZARD && check_fpr_hazard_field(ins.hart, ins.issue, 1) == HAZARD_FIELD_RS3) ? 6 : 0
    ) iff (ins.trap == 0) {
        bins no_hazard      = {0};
        bins raw_fs1_depth0 = {1};
        bins raw_fs2_depth0 = {2};
        bins raw_fs3_depth0 = {3};
        bins raw_fs1_depth1 = {4};
        bins raw_fs2_depth1 = {5};
        bins raw_fs3_depth1 = {6};
        bins waw_depth0     = {7};
    }
