    //////////////////////////////////////////////////////////////////////////////////
    // cp_custom_ordered_index_overlap
    //////////////////////////////////////////////////////////////////////////////////

    // Custom coverpoints for Vector indexed load stores with overlaps in the index register

    index_register_data_overlap: coverpoint data_overlap(ins.hart, ins.issue, ins.current.insn[14:12], ins.current.vs2_val) iff (ins.trap == 0) {
        bins no_overlap = {0};
        bins overlap = {1};
    }

    //// end cp_custom_ordered_index_overlap ////////////////////////////////////////////////
