    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_vfclass_onehot
    //////////////////////////////////////////////////////////////////////////////////

    vfclass_64onehot: coverpoint $clog2(get_vr_element_zero(ins.hart, ins.issue, ins.current.vd_val))
                      iff ($onehot(get_vr_element_zero(ins.hart, ins.issue, ins.current.vd_val))) {
        bins b_1[] = { [0:9] };
    }

    cp_custom_vfclass_onehot : cross std_vec, vfclass_64onehot;

    //// cp_custom_vfclass_onehot////////////////////////////////////////////////
