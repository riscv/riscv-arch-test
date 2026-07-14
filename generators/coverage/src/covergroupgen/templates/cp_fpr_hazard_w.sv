    cp_fpr_hazard_w : coverpoint check_fpr_hazards(ins.hart, ins.issue, 1)  iff (ins.trap == 0 )  {
        bins no_hazard  = {NO_HAZARD};
        bins waw_hazard = {WAW_HAZARD};
        bins war_hazard = {WAR_HAZARD};
    }
