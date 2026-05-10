    // Custom coverpoints for Store Conditional


    cp_prev_lr : coverpoint ((ins.prev.inst_name == "lr.w" & ins.current.inst_name == "sc.w") | (ins.prev.inst_name == "lr.d" & ins.current.inst_name == "sc.d")) {
        bins lr_sc_size_match = {1};
    }

    cp_sc_pass_fail : coverpoint (ins.current.rd_val) {
        bins pass = {0};
        bins fail = {[1:$]};
    }
    cp_address_difference : coverpoint {ins.current.rs1_val - ins.prev.rs1_val}[7:3] iff (ins.current.rs1_val[31:8] == ins.prev.rs1_val[31:8]) {
        // difference between lr and sc address may or may not fall in reservation set size
    }
    cp_custom_aqrl : coverpoint ins.current.insn[26:25]  iff (ins.trap == 0 )  {
        // Combinations of acquire and release
        ignore_bins aq_norl = {2'b10};
    }
    cp_custom_sc_after_sc : coverpoint (ins.prev.inst_name == "sc.w" | ins.prev.inst_name == "sc.d") {
        // previous instruction was store conditional
    }
    cp_custom_sc_lr : cross cp_prev_lr, cp_sc_pass_fail;
    cp_custom_sc_addresses : cross cp_prev_lr, cp_address_difference;
